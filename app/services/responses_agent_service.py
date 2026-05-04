"""Responses API service with file search and optional Firecrawl MCP."""

import logging
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI

from app.services.file_search_agent_service import WORKSPACE_AGENT_PROMPT

logger = logging.getLogger(__name__)


class ResponsesAgentService:
    """Runs workspace chat through the OpenAI Responses API."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o")
        self.firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY", "").strip()

    def _build_tools(self, vector_store_id: str, max_num_results: int) -> List[Dict[str, Any]]:
        tools: List[Dict[str, Any]] = [
            {
                "type": "file_search",
                "vector_store_ids": [vector_store_id],
                "max_num_results": max_num_results,
            }
        ]

        if self.firecrawl_api_key:
            tools.append(
                {
                    "type": "mcp",
                    "server_label": "firecrawl",
                    "server_description": "Web scraping and search via Firecrawl MCP server.",
                    "server_url": f"https://mcp.firecrawl.dev/{self.firecrawl_api_key}/v2/mcp",
                    "require_approval": "never",
                }
            )

        return tools

    def _extract_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        tool_calls = []
        for item in getattr(response, "output", []):
            item_type = getattr(item, "type", None)
            if item_type == "file_search_call":
                tool_calls.append(
                    {
                        "tool_name": "file_search",
                        "tool_type": item_type,
                        "call_id": getattr(item, "id", None),
                        "queries": getattr(item, "queries", []),
                        "status": getattr(item, "status", None),
                    }
                )
            elif item_type == "mcp_call":
                tool_calls.append(
                    {
                        "tool_name": getattr(item, "name", None) or "mcp",
                        "tool_type": item_type,
                        "call_id": getattr(item, "id", None),
                        "server_label": getattr(item, "server_label", None),
                        "status": getattr(item, "status", None),
                    }
                )
            elif item_type == "mcp_list_tools":
                tool_calls.append(
                    {
                        "tool_name": "mcp_list_tools",
                        "tool_type": item_type,
                        "call_id": getattr(item, "id", None),
                        "server_label": getattr(item, "server_label", None),
                        "status": getattr(item, "status", None),
                    }
                )
        return tool_calls

    def _extract_usage(self, response: Any) -> Dict[str, Any]:
        usage = getattr(response, "usage", None)
        if usage is None:
            return {}
        if hasattr(usage, "model_dump"):
            return usage.model_dump()
        return {
            "input_tokens": getattr(usage, "input_tokens", 0),
            "output_tokens": getattr(usage, "output_tokens", 0),
            "total_tokens": getattr(usage, "total_tokens", 0),
        }

    def answer(
        self,
        vector_store_id: str,
        question: str,
        max_num_results: int = 5,
        previous_response_id: Optional[str] = None,
        store: bool = True,
    ) -> Dict[str, Any]:
        request: Dict[str, Any] = {
            "model": self.model,
            "instructions": WORKSPACE_AGENT_PROMPT,
            "input": question,
            "tools": self._build_tools(vector_store_id, max_num_results),
            "store": store,
        }
        if previous_response_id:
            request["previous_response_id"] = previous_response_id

        response = self.client.responses.create(**request)
        tool_calls = self._extract_tool_calls(response)

        logger.info(
            "responses_query_tool_usage vector_store_id=%s response_id=%s tools=%s",
            vector_store_id,
            response.id,
            tool_calls,
        )

        return {
            "answer": response.output_text,
            "response_id": response.id,
            "previous_response_id": previous_response_id,
            "usage": self._extract_usage(response),
            "tool_calls": tool_calls,
        }
