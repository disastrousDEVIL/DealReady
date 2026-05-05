"""Firecrawl integration for URL-to-Markdown ingestion."""

import json
import os
import time
from typing import Any, Dict
from urllib.parse import urljoin, urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class FirecrawlService:
    """Crawls URLs through Firecrawl and returns Markdown content."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("FIRECRAWL_API_KEY", "").strip()
        if not self.api_key:
            raise ValueError("FIRECRAWL_API_KEY not found in environment")

    def _post(self, path: str, payload: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
        request = Request(
            f"https://api.firecrawl.dev/v2/{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ValueError(f"Firecrawl {path} failed: {detail}") from exc
        except URLError as exc:
            raise ValueError(f"Firecrawl {path} failed: {exc.reason}") from exc

        return json.loads(body)

    def _get(self, url: str, timeout: int = 60) -> Dict[str, Any]:
        request = Request(url, headers={"Authorization": f"Bearer {self.api_key}"})
        try:
            with urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ValueError(f"Firecrawl crawl status failed: {detail}") from exc
        except URLError as exc:
            raise ValueError(f"Firecrawl crawl status failed: {exc.reason}") from exc

        return json.loads(body)

    def scrape_markdown(self, url: str) -> Dict[str, Any]:
        payload = json.dumps(
            {
                "url": url,
                "formats": ["markdown"],
                "onlyMainContent": True,
                "timeout": 30000,
            }
        ).encode("utf-8")

        request = Request(
            "https://api.firecrawl.dev/v2/scrape",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=60) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ValueError(f"Firecrawl scrape failed: {detail}") from exc
        except URLError as exc:
            raise ValueError(f"Firecrawl scrape failed: {exc.reason}") from exc

        result = json.loads(body)
        data = result.get("data", result)
        markdown = data.get("markdown") or result.get("markdown")
        if not markdown:
            raise ValueError("Firecrawl did not return markdown content for the URL.")

        return {
            "markdown": markdown,
            "metadata": data.get("metadata", {}),
            "source_url": data.get("metadata", {}).get("sourceURL") or url,
        }

    def _run_crawl(
        self,
        url: str,
        limit: int = 10,
        crawl_entire_domain: bool = True,
        poll_interval_seconds: int = 5,
        timeout_seconds: int = 180,
    ) -> Dict[str, Any]:
        crawl = self._post(
            "crawl",
            {
                "url": url,
                "limit": limit,
                "crawlEntireDomain": crawl_entire_domain,
                "allowExternalLinks": False,
                "allowSubdomains": False,
                "ignoreQueryParameters": True,
                "excludePaths": ["sitemap", ".xml"],
                "scrapeOptions": {
                    "formats": ["markdown"],
                    "onlyMainContent": True,
                    "timeout": 30000,
                },
            },
        )

        status_url = crawl.get("url")
        if not status_url:
            raise ValueError("Firecrawl did not return a crawl status URL.")

        deadline = time.monotonic() + timeout_seconds
        status = crawl
        while time.monotonic() < deadline:
            status = self._get(status_url)
            if status.get("status") == "completed":
                break
            if status.get("status") in {"failed", "cancelled"}:
                raise ValueError(f"Firecrawl crawl ended with status: {status.get('status')}")
            time.sleep(poll_interval_seconds)
        else:
            raise ValueError("Firecrawl crawl timed out.")

        return status

    def crawl_markdown(
        self,
        url: str,
        limit: int = 10,
        blog_limit: int = 5,
        poll_interval_seconds: int = 5,
        timeout_seconds: int = 180,
    ) -> Dict[str, Any]:
        statuses = [
            self._run_crawl(
                url,
                limit=limit,
                crawl_entire_domain=True,
                poll_interval_seconds=poll_interval_seconds,
                timeout_seconds=timeout_seconds,
            )
        ]

        parsed = urlparse(url)
        blog_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/blog/")
        if blog_url.rstrip("/") != url.rstrip("/"):
            try:
                statuses.append(
                    self._run_crawl(
                        blog_url,
                        limit=blog_limit,
                        crawl_entire_domain=False,
                        poll_interval_seconds=poll_interval_seconds,
                        timeout_seconds=timeout_seconds,
                    )
                )
            except ValueError:
                # Many sites do not use /blog/. The main crawl still gives useful company data.
                pass

        pages = []
        seen_urls = set()
        for status in statuses:
            documents = status.get("data", [])
            for index, document in enumerate(documents, start=1):
                markdown = document.get("markdown")
                if not markdown:
                    continue
                metadata = document.get("metadata", {})
                source_url = metadata.get("sourceURL") or document.get("url") or url
                parsed_source = urlparse(source_url)
                if "sitemap" in parsed_source.path or parsed_source.path.endswith(".xml"):
                    continue
                normalized_url = source_url.rstrip("/")
                if normalized_url in seen_urls:
                    continue
                seen_urls.add(normalized_url)
                pages.append(
                    {
                        "source_url": source_url,
                        "title": metadata.get("title") or f"Page {index}",
                        "markdown": markdown,
                    }
                )

        if not pages:
            raise ValueError("Firecrawl crawl did not return markdown content.")

        combined = []
        for page in pages:
            combined.append(f"# {page['title']}\n\nSource: {page['source_url']}\n\n{page['markdown']}")

        return {
            "markdown": "\n\n---\n\n".join(combined),
            "pages": pages,
            "source_url": url,
            "completed": sum(status.get("completed") or 0 for status in statuses),
            "total": sum(status.get("total") or 0 for status in statuses),
            "credits_used": sum(status.get("creditsUsed") or 0 for status in statuses),
        }
