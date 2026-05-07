"""Demo chatbot endpoints."""

from datetime import datetime, timedelta
import os
import re
import secrets
import tempfile
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_vector_store_service
from app.models.demo import AgentDemoFileORM, AgentDemoORM, DemoFileStatus, DemoFileType, DemoStatus
from app.schemas.demo import (
    DemoAuthRequest,
    DemoAuthResponse,
    DemoCreateResponse,
    DemoQueryRequest,
    DemoQueryResponse,
    DemoResponse,
)
from app.services.demo_lifecycle_service import DemoLifecycleService
from app.services.firecrawl_service import FirecrawlService
from app.services.responses_agent_service import ResponsesAgentService
from app.services.vector_store_service import VectorStoreService

router = APIRouter(prefix="/demos", tags=["demos"])

MAX_PDF_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_PDFS_PER_DEMO = 5
DEMO_TTL_DAYS = 7
OPENAI_CITATION_MARKER_RE = re.compile(r"(?:[^]*|\s*�filecite�[^\s]*)")


def _chat_url(slug: str) -> str:
    return f"/demos/{slug}/chat"


def _markdown_filename_from_url(target_url: str) -> str:
    parsed = urlparse(target_url)
    host = parsed.netloc.replace(":", "_") or "website"
    return f"{host}.md"


def _validate_url(target_url: str) -> None:
    parsed = urlparse(target_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="A valid http(s) company_url is required.")


def _demo_response(demo: AgentDemoORM) -> DemoResponse:
    return DemoResponse(
        id=demo.id,
        prospect_name=demo.prospect_name,
        company_url=demo.company_url,
        logo_url=demo.logo_url,
        public_slug=demo.public_slug,
        chat_url=_chat_url(demo.public_slug),
        status=demo.status,
        expires_at=demo.expires_at,
        created_at=demo.created_at,
    )


def _replace_citation_metadata(result: dict, file_meta_by_id: dict[str, dict]) -> dict:
    answer = result.get("answer", "")
    extra_url_citations = []
    for citation in result.get("citations", []):
        file_id = citation.get("file_id")
        metadata = file_meta_by_id.get(file_id)
        if not metadata:
            continue
        original_name = metadata.get("filename")
        old_name = citation.get("filename")
        if old_name:
            answer = answer.replace(old_name, original_name)
        citation["filename"] = original_name
        if metadata.get("source_url"):
            plain_line = f"[{citation['number']}] {original_name}"
            next_number = len(result.get("citations", [])) + len(extra_url_citations) + 1
            url_citation = {
                "type": "url",
                "url": metadata["source_url"],
                "title": original_name,
                "number": next_number,
            }
            extra_url_citations.append(url_citation)
            answer = answer.replace(plain_line, f"{plain_line}\n[{next_number}] {metadata['source_url']}")
    if extra_url_citations:
        result["citations"] = result.get("citations", []) + extra_url_citations
    result["answer"] = answer
    return result


def _clean_answer_text(answer: str) -> str:
    cleaned = OPENAI_CITATION_MARKER_RE.sub("", answer)
    return re.sub(r"[ \t]{2,}", " ", cleaned).strip()


async def _validate_pdfs(files: Optional[List[UploadFile]]) -> list[tuple[str, bytes]]:
    pdf_uploads = [upload for upload in files or [] if upload.filename]
    if len(pdf_uploads) > MAX_PDFS_PER_DEMO:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_PDFS_PER_DEMO} PDFs are allowed per demo.",
        )

    validated = []
    for upload in pdf_uploads:
        filename = upload.filename or "uploaded_file.pdf"
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
        content = await upload.read()
        if len(content) > MAX_PDF_UPLOAD_BYTES:
            raise HTTPException(status_code=400, detail="PDF size must be 25 MB or less.")
        validated.append((filename, content))
    return validated


@router.get("", response_model=list[DemoResponse])
async def list_active_demos(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    demos = (
        db.query(AgentDemoORM)
        .filter(AgentDemoORM.status == DemoStatus.ACTIVE, AgentDemoORM.expires_at > now)
        .order_by(AgentDemoORM.created_at.desc())
        .all()
    )
    return [_demo_response(demo) for demo in demos]


@router.post("", response_model=DemoCreateResponse)
async def create_demo(
    prospect_name: str = Form(...),
    company_url: str = Form(...),
    logo_url: Optional[str] = Form(default=None),
    files: List[UploadFile] = File(
        default_factory=list,
        description=f"Optional PDF uploads. Maximum {MAX_PDFS_PER_DEMO} files, {MAX_PDF_UPLOAD_BYTES // (1024 * 1024)} MB each.",
        json_schema_extra={"items": {"type": "string", "format": "binary"}},
    ),
    db: Session = Depends(get_db),
    vector_service: VectorStoreService = Depends(get_vector_store_service),
):
    _validate_url(company_url)
    validated_pdfs = await _validate_pdfs(files)

    public_slug = secrets.token_urlsafe(8)
    generated_password = secrets.token_urlsafe(8)
    expires_at = datetime.utcnow() + timedelta(days=DEMO_TTL_DAYS)
    vector_store_id = vector_service.create_workspace_vector_store(prospect_name)
    temp_paths = []
    indexed_files = []
    demo = AgentDemoORM(
        prospect_name=prospect_name,
        company_url=company_url,
        logo_url=logo_url,
        vector_store_id=vector_store_id,
        public_slug=public_slug,
        access_password=generated_password,
        status=DemoStatus.ACTIVE,
        expires_at=expires_at,
    )

    try:
        firecrawl = FirecrawlService()
        crawl = firecrawl.crawl_markdown(company_url)
        markdown_name = _markdown_filename_from_url(crawl["source_url"])
        markdown_content = f"# Crawled content from {crawl['source_url']}\n\n{crawl['markdown']}\n"

        with tempfile.NamedTemporaryFile(delete=False, suffix=".md", mode="w", encoding="utf-8") as tmp:
            tmp.write(markdown_content)
            temp_paths.append(tmp.name)
            markdown_path = tmp.name

        file_id = vector_service.upload_file(markdown_path)
        vector_store_file_id = vector_service.add_file_to_vector_store(vector_store_id, file_id)

        db.add(demo)
        db.flush()
        db.add(
            AgentDemoFileORM(
                demo_id=demo.id,
                file_id=file_id,
                vector_store_file_id=vector_store_file_id,
                original_name=markdown_name,
                file_type=DemoFileType.URL,
                source_url=crawl["source_url"],
                size_bytes=len(markdown_content.encode("utf-8")),
                status=DemoFileStatus.COMPLETED,
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

            file_id = vector_service.upload_file(tmp_path)
            vector_store_file_id = vector_service.add_file_to_vector_store(vector_store_id, file_id)
            db.add(
                AgentDemoFileORM(
                    demo_id=demo.id,
                    file_id=file_id,
                    vector_store_file_id=vector_store_file_id,
                    original_name=filename,
                    file_type=DemoFileType.PDF,
                    source_url=None,
                    size_bytes=len(content),
                    status=DemoFileStatus.COMPLETED,
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
        db.refresh(demo)
        return DemoCreateResponse(
            **_demo_response(demo).model_dump(),
            vector_store_id=demo.vector_store_id,
            generated_password=generated_password,
            indexed_files=indexed_files,
            pages_crawled=len(crawl["pages"]),
        )
    except Exception:
        db.rollback()
        try:
            vector_service.delete_workspace_vector_store(vector_store_id)
        except Exception:
            pass
        raise
    finally:
        for path in temp_paths:
            if os.path.exists(path):
                os.unlink(path)


@router.get("/{slug}", response_model=DemoResponse)
async def get_demo(slug: str, db: Session = Depends(get_db)):
    demo = db.query(AgentDemoORM).filter(AgentDemoORM.public_slug == slug).first()
    if demo is None:
        raise HTTPException(status_code=404, detail="Demo not found")
    if demo.status != DemoStatus.ACTIVE or demo.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=410, detail="Demo link has expired")
    return _demo_response(demo)


@router.post("/{slug}/auth", response_model=DemoAuthResponse)
async def authenticate_demo(slug: str, payload: DemoAuthRequest, db: Session = Depends(get_db)):
    demo = db.query(AgentDemoORM).filter(AgentDemoORM.public_slug == slug).first()
    if demo is None:
        raise HTTPException(status_code=404, detail="Demo not found")
    if demo.status != DemoStatus.ACTIVE or demo.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=410, detail="Demo link has expired")

    requires_password = bool(demo.access_password)
    if not requires_password:
        return DemoAuthResponse(authenticated=True, requires_password=False)
    if payload.access_password and payload.access_password == demo.access_password:
        return DemoAuthResponse(authenticated=True, requires_password=True)
    raise HTTPException(status_code=401, detail="Invalid demo password")


@router.post("/{slug}/query", response_model=DemoQueryResponse)
async def query_demo(slug: str, query: DemoQueryRequest, db: Session = Depends(get_db)):
    demo = db.query(AgentDemoORM).filter(AgentDemoORM.public_slug == slug).first()
    if demo is None:
        raise HTTPException(status_code=404, detail="Demo not found")
    if demo.status != DemoStatus.ACTIVE or demo.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=410, detail="Demo link has expired")
    if demo.access_password and query.access_password != demo.access_password:
        raise HTTPException(status_code=401, detail="Invalid demo password")

    result = ResponsesAgentService().answer(
        vector_store_id=demo.vector_store_id,
        question=query.question,
        max_num_results=query.max_results,
        previous_response_id=query.previous_response_id,
        store=query.store,
        demo_context=(
            f"Prospect name: {demo.prospect_name}\n"
            f"Company URL: {demo.company_url}\n"
            "The answer should be useful to someone evaluating this prospect demo."
        ),
    )
    files = db.query(AgentDemoFileORM).filter(AgentDemoFileORM.demo_id == demo.id).all()
    file_meta_by_id = {
        file_rec.file_id: {
            "filename": file_rec.original_name,
            "source_url": file_rec.source_url
            or (demo.company_url if file_rec.file_type == DemoFileType.URL else None),
        }
        for file_rec in files
    }
    result = _replace_citation_metadata(result, file_meta_by_id)
    return DemoQueryResponse(
        answer=_clean_answer_text(result["answer"]),
        response_id=result["response_id"],
        previous_response_id=result.get("previous_response_id"),
        citations=result.get("citations", []),
        usage=result.get("usage", {}),
        tool_calls=result.get("tool_calls", []),
    )


@router.delete("/{demo_id}")
async def disable_demo(
    demo_id: str,
    db: Session = Depends(get_db),
    vector_service: VectorStoreService = Depends(get_vector_store_service),
):
    demo = db.get(AgentDemoORM, demo_id)
    if demo is None:
        raise HTTPException(status_code=404, detail="Demo not found")

    demo.status = DemoStatus.DISABLED
    try:
        vector_service.delete_workspace_vector_store(demo.vector_store_id)
    except Exception:
        pass
    db.commit()
    return {"status": "disabled", "demo_id": str(demo.id)}


@router.post("/maintenance/expire")
async def expire_demo_links(
    db: Session = Depends(get_db),
    vector_service: VectorStoreService = Depends(get_vector_store_service),
):
    return DemoLifecycleService(db=db, vector_service=vector_service).expire_due_demos()
