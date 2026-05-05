"""OpenAI vector store service."""

import logging
import os
from enum import Enum
from typing import Any, Dict, List, Optional

from openai import APIConnectionError, APIError, OpenAI

logger = logging.getLogger(__name__)


class FileStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VectorStoreService:
    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o")
        self.default_chunking = {
            "type": "static",
            "static": {"max_chunk_size_tokens": 800, "chunk_overlap_tokens": 400},
        }

    def create_workspace_vector_store(self, workspace_name: str) -> str:
        vs = self.client.vector_stores.create(
            name=workspace_name,
            expires_after={"anchor": "last_active_at", "days": 30},
        )
        return vs.id

    def get_vector_store(self, vector_store_id: str) -> Dict[str, Any]:
        vs = self.client.vector_stores.retrieve(vector_store_id)
        return {
            "id": vs.id,
            "name": vs.name,
            "created_at": vs.created_at,
            "file_counts": {
                "in_progress": vs.file_counts.in_progress,
                "completed": vs.file_counts.completed,
                "failed": vs.file_counts.failed,
            },
        }

    def delete_workspace_vector_store(self, vector_store_id: str) -> bool:
        return self.client.vector_stores.delete(vector_store_id).deleted

    def upload_file(self, file_path: str, purpose: str = "assistants") -> str:
        with open(file_path, "rb") as f:
            response = self.client.files.create(file=f, purpose=purpose)
        return response.id

    def add_file_to_vector_store(self, vector_store_id: str, file_id: str) -> str:
        vs_file = self.client.vector_stores.files.create_and_poll(
            vector_store_id=vector_store_id,
            file_id=file_id,
            chunking_strategy=self.default_chunking,
        )
        if vs_file.status != "completed":
            error = getattr(vs_file, "last_error", None)
            message = getattr(error, "message", None) or f"Vector store file status: {vs_file.status}"
            raise ValueError(f"File indexing failed or did not complete. {message}")
        return vs_file.id

    def delete_file_from_vector_store(self, vector_store_id: str, vector_store_file_id: str) -> bool:
        return self.client.vector_stores.files.delete(
            vector_store_id=vector_store_id,
            file_id=vector_store_file_id,
        ).deleted

    def list_vector_store_files(self, vector_store_id: str) -> List[Dict[str, Any]]:
        files = self.client.vector_stores.files.list(vector_store_id)
        return [{"id": f.id, "status": f.status, "created_at": f.created_at} for f in files.data]

    def query_workspace(
        self,
        vector_store_id: str,
        question: str,
        include_search_results: bool = True,
    ) -> Dict[str, Any]:
        response = self.client.responses.create(
            model=self.model,
            input=question,
            tools=[{"type": "file_search", "vector_store_ids": [vector_store_id]}],
            include=["output[*].file_search_call.search_results"] if include_search_results else [],
        )

        answer_text = ""
        citations: List[Dict[str, str]] = []
        search_results: List[Any] = []

        for output in response.output:
            if getattr(output, "type", None) == "message" and getattr(output, "content", None):
                first = output.content[0]
                if getattr(first, "type", None) == "output_text":
                    answer_text = first.text
            if (
                getattr(output, "type", None) == "file_search_call"
                and include_search_results
                and hasattr(output, "search_results")
            ):
                search_results = output.search_results

        return {
            "answer": answer_text,
            "citations": citations,
            "search_results": search_results,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        }

    def health_check(self) -> bool:
        try:
            self.client.models.list()
            return True
        except APIConnectionError:
            return False
        except APIError:
            return False
