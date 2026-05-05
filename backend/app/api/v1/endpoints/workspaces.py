"""Workspace endpoints."""

import os
import tempfile
from typing import List, Optional
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_vector_store_service
from app.models.workspace import FileStatus, WorkspaceFileORM, WorkspaceORM
from app.schemas.workspace import (
    AgentQueryResponse,
    QueryRequest,
    QueryResponse,
    ResponsesQueryRequest,
    ResponsesQueryResponse,
    WorkspaceCreate,
    WorkspaceFileResponse,
    WorkspaceResponse,
)
from app.services.firecrawl_service import FirecrawlService
from app.services.vector_store_service import VectorStoreService
from app.services.file_search_agent_service import FileSearchAgentService
from app.services.responses_agent_service import ResponsesAgentService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

MAX_PDF_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_PDFS_PER_WORKSPACE = 5


def _markdown_filename_from_url(target_url: str) -> str:
    parsed = urlparse(target_url)
    host = parsed.netloc.replace(":", "_") or "website"
    return f"{host}.md"


def _replace_citation_filenames(result: dict, file_name_by_id: dict[str, str]) -> dict:
    answer = result.get("answer", "")
    for citation in result.get("citations", []):
        file_id = citation.get("file_id")
        original_name = file_name_by_id.get(file_id)
        if not original_name:
            continue
        old_name = citation.get("filename")
        if old_name:
            answer = answer.replace(old_name, original_name)
        citation["filename"] = original_name
    result["answer"] = answer
    return result


@router.post("", response_model=WorkspaceResponse)
async def create_workspace(
    workspace: WorkspaceCreate,
    db: Session = Depends(get_db),
    service: VectorStoreService = Depends(get_vector_store_service),
):
    try:
        vector_store_id = service.create_workspace_vector_store(workspace.name)
        record = WorkspaceORM(
            name=workspace.name,
            owner_id=workspace.owner_id,
            vector_store_id=vector_store_id,
            description=workspace.description,
            is_active=True,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return WorkspaceResponse(
            id=record.id,
            name=record.name,
            owner_id=record.owner_id,
            vector_store_id=vector_store_id,
            description=record.description,
            file_count=0,
            created_at=record.created_at,
            updated_at=record.updated_at,
            is_active=record.is_active,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    service: VectorStoreService = Depends(get_vector_store_service),
):
    try:
        workspace = db.get(WorkspaceORM, workspace_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        vs_data = service.get_vector_store(workspace.vector_store_id)
        return WorkspaceResponse(
            id=workspace.id,
            name=workspace.name or vs_data.get("name", "Workspace"),
            owner_id=workspace.owner_id,
            vector_store_id=workspace.vector_store_id,
            description=workspace.description,
            file_count=vs_data.get("file_counts", {}).get("completed", 0),
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
            is_active=workspace.is_active,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    service: VectorStoreService = Depends(get_vector_store_service),
):
    try:
        workspace = db.get(WorkspaceORM, workspace_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        service.delete_workspace_vector_store(workspace.vector_store_id)
        db.delete(workspace)
        db.commit()
        return {"status": "deleted", "workspace_id": str(workspace_id)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{workspace_id}/upload")
async def upload_file(
    workspace_id: UUID,
    target_url: str = Form(...),
    files: Optional[List[UploadFile]] = File(default=None),
    db: Session = Depends(get_db),
    service: VectorStoreService = Depends(get_vector_store_service),
):
    try:
        workspace = db.get(WorkspaceORM, workspace_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        parsed_url = urlparse(target_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise HTTPException(status_code=400, detail="A valid http(s) target_url is required.")

        pdf_uploads = [upload for upload in files or [] if upload.filename]
        existing_pdf_count = (
            db.query(WorkspaceFileORM)
            .filter(
                WorkspaceFileORM.workspace_id == workspace_id,
                WorkspaceFileORM.file_type == "pdf",
            )
            .count()
        )
        if existing_pdf_count >= MAX_PDFS_PER_WORKSPACE:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum {MAX_PDFS_PER_WORKSPACE} PDFs are allowed per workspace.",
            )

        if existing_pdf_count + len(pdf_uploads) > MAX_PDFS_PER_WORKSPACE:
            remaining = MAX_PDFS_PER_WORKSPACE - existing_pdf_count
            raise HTTPException(
                status_code=400,
                detail=f"You can upload {remaining} more PDF(s) to this workspace.",
            )

        validated_pdfs = []
        for upload in pdf_uploads:
            filename = upload.filename or "uploaded_file.pdf"
            if not filename.lower().endswith(".pdf"):
                raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

            content = await upload.read()
            if len(content) > MAX_PDF_UPLOAD_BYTES:
                raise HTTPException(status_code=400, detail="PDF size must be 25 MB or less.")
            validated_pdfs.append((filename, content))

        indexed_files = []
        temp_paths = []
        firecrawl = FirecrawlService()
        crawl = firecrawl.crawl_markdown(target_url)
        markdown_name = _markdown_filename_from_url(crawl["source_url"])
        markdown_content = f"# Crawled content from {crawl['source_url']}\n\n{crawl['markdown']}\n"

        try:
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".md",
                mode="w",
                encoding="utf-8",
            ) as tmp:
                tmp.write(markdown_content)
                temp_paths.append(tmp.name)
                markdown_path = tmp.name

            file_id = service.upload_file(markdown_path)
            vector_store_file_id = service.add_file_to_vector_store(
                workspace.vector_store_id, file_id
            )
            db.add(
                WorkspaceFileORM(
                    workspace_id=workspace.id,
                    file_id=file_id,
                    vector_store_file_id=vector_store_file_id,
                    original_name=markdown_name,
                    file_type="url",
                    size_bytes=len(markdown_content.encode("utf-8")),
                    status=FileStatus.COMPLETED,
                )
            )
            indexed_files.append(
                {
                    "source": "url",
                    "file_id": file_id,
                    "vector_store_file_id": vector_store_file_id,
                    "original_name": markdown_name,
                    "source_url": crawl["source_url"],
                    "pages_crawled": len(crawl["pages"]),
                }
            )

            for filename, content in validated_pdfs:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(content)
                    temp_paths.append(tmp.name)
                    tmp_path = tmp.name

                file_id = service.upload_file(tmp_path)
                vector_store_file_id = service.add_file_to_vector_store(
                    workspace.vector_store_id, file_id
                )
                db.add(
                    WorkspaceFileORM(
                        workspace_id=workspace.id,
                        file_id=file_id,
                        vector_store_file_id=vector_store_file_id,
                        original_name=filename,
                        file_type="pdf",
                        size_bytes=len(content),
                        status=FileStatus.COMPLETED,
                    )
                )
                indexed_files.append(
                    {
                        "source": "pdf",
                        "file_id": file_id,
                        "vector_store_file_id": vector_store_file_id,
                        "original_name": filename,
                    }
                )

            db.commit()
            return {
                "status": "uploaded",
                "workspace_id": str(workspace.id),
                "target_url": target_url,
                "pages_crawled": len(crawl["pages"]),
                "indexed_files": indexed_files,
                "message": "URL content and PDFs indexed successfully.",
            }
        finally:
            for path in temp_paths:
                if os.path.exists(path):
                    os.unlink(path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/files", response_model=List[WorkspaceFileResponse])
async def list_workspace_files(
    workspace_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        files = (
            db.query(WorkspaceFileORM)
            .filter(WorkspaceFileORM.workspace_id == workspace_id)
            .order_by(WorkspaceFileORM.created_at.desc())
            .all()
        )
        return [WorkspaceFileResponse.model_validate(file_rec) for file_rec in files]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{workspace_id}/files/{file_id}")
async def delete_file(
    workspace_id: UUID,
    file_id: UUID,
    db: Session = Depends(get_db),
    service: VectorStoreService = Depends(get_vector_store_service),
):
    try:
        workspace = db.get(WorkspaceORM, workspace_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        workspace_file = db.get(WorkspaceFileORM, file_id)
        if workspace_file is None or workspace_file.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="File not found")

        service.delete_file_from_vector_store(
            workspace.vector_store_id, workspace_file.vector_store_file_id
        )
        db.delete(workspace_file)
        db.commit()
        return {"status": "deleted", "file_id": str(file_id)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{workspace_id}/query", response_model=QueryResponse)
async def query_workspace(
    workspace_id: UUID,
    query: QueryRequest,
    db: Session = Depends(get_db),
    service: VectorStoreService = Depends(get_vector_store_service),
):
    try:
        workspace = db.get(WorkspaceORM, workspace_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        result = service.query_workspace(
            vector_store_id=workspace.vector_store_id,
            question=query.question,
            include_search_results=query.include_search_results,
        )
        return QueryResponse(
            answer=result["answer"],
            citations=result["citations"],
            search_results=result.get("search_results", []),
            usage=result["usage"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{workspace_id}/agent-query", response_model=AgentQueryResponse)
async def agent_query_workspace(
    workspace_id: UUID,
    query: QueryRequest,
    db: Session = Depends(get_db),
):
    try:
        workspace = db.get(WorkspaceORM, workspace_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        agent_service = FileSearchAgentService()
        result = await agent_service.answer_from_vector_store(
            vector_store_id=workspace.vector_store_id,
            question=query.question,
            max_num_results=query.max_results,
        )
        return AgentQueryResponse(
            answer=result["answer"],
            citations=result.get("citations", []),
            usage=result.get("usage", {}),
            tool_calls=result.get("tool_calls", []),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{workspace_id}/responses-query", response_model=ResponsesQueryResponse)
async def responses_query_workspace(
    workspace_id: UUID,
    query: ResponsesQueryRequest,
    db: Session = Depends(get_db),
):
    try:
        workspace = db.get(WorkspaceORM, workspace_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        responses_service = ResponsesAgentService()
        result = responses_service.answer(
            vector_store_id=workspace.vector_store_id,
            question=query.question,
            max_num_results=query.max_results,
            previous_response_id=query.previous_response_id,
            store=query.store,
        )
        files = (
            db.query(WorkspaceFileORM)
            .filter(WorkspaceFileORM.workspace_id == workspace_id)
            .all()
        )
        file_name_by_id = {file_rec.file_id: file_rec.original_name for file_rec in files}
        result = _replace_citation_filenames(result, file_name_by_id)
        return ResponsesQueryResponse(
            answer=result["answer"],
            response_id=result["response_id"],
            previous_response_id=result.get("previous_response_id"),
            citations=result.get("citations", []),
            usage=result.get("usage", {}),
            tool_calls=result.get("tool_calls", []),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
