"""
tools.py
--------

Serper.dev search wrapper used by the Research Agent.

Improvements:
- Better error handling
- Duplicate removal
- Cleaner output formatting
- Handles malformed API responses
- LLM-friendly search summaries
"""

from typing import Set

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from config import Config, logger


# ------------------------------------------------------------------
# Tool Input Schema
# ------------------------------------------------------------------


class SerperSearchInput(BaseModel):
    """
    Schema for CrewAI.
    """

    query: str = Field(
        ...,
        description="Search query",
    )


# ------------------------------------------------------------------
# Serper Tool
# ------------------------------------------------------------------


class SerperSearchTool(BaseTool):

    name: str = "web_search"

    description: str = (
        "Search the web for factual and recent information "
        "about companies, people, products and industries."
    )

    args_schema: type[BaseModel] = SerperSearchInput

    def _run(
        self,
        query: str,
    ) -> str:

        logger.info("Running Serper search: %s", query)

        url = "https://google.serper.dev/search"

        headers = {
            "X-API-KEY": Config.SERPER_API_KEY,
            "Content-Type": "application/json",
        }

        payload = {
            "q": query,
            "num": 8,
        }

        # ----------------------------------------------------------

        try:

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=20,
            )

        except requests.exceptions.RequestException as e:

            logger.warning(
                "Serper request failed: %s",
                e,
            )

            return (
                f"SEARCH_ERROR: {e}"
            )

        # ----------------------------------------------------------

        if response.status_code in (
            401,
            403,
        ):

            raise RuntimeError(
                "Invalid SERPER_API_KEY."
            )

        if response.status_code != 200:

            logger.warning(
                "Serper returned status %s",
                response.status_code,
            )

            return (
                f"SEARCH_ERROR: status "
                f"{response.status_code}"
            )

        # ----------------------------------------------------------

        try:

            data = response.json()

        except Exception:

            logger.warning(
                "Invalid JSON returned from Serper."
            )

            return (
                "SEARCH_ERROR: invalid JSON"
            )

        organic = data.get(
            "organic",
            [],
        )

        if not organic:

            logger.warning(
                "No search results for '%s'",
                query,
            )

            return "NO_RESULTS_FOUND"

        # ----------------------------------------------------------
        # Build compact search summary
        # ----------------------------------------------------------

        seen_links: Set[str] = set()

        results = []

        for result in organic:

            title = (
                result.get("title", "")
                .strip()
            )

            snippet = (
                result.get("snippet", "")
                .strip()
            )

            link = (
                result.get("link", "")
                .strip()
            )

            if not link:
                continue

            if link in seen_links:
                continue

            seen_links.add(link)

            if (
                len(title) == 0
                and len(snippet) == 0
            ):
                continue

            block = []

            if title:
                block.append(
                    f"Title: {title}"
                )

            if snippet:
                block.append(
                    f"Summary: {snippet}"
                )

            block.append(
                f"Source: {link}"
            )

            results.append(
                "\n".join(block)
            )

        if not results:

            return "NO_RESULTS_FOUND"

        logger.info(
            "Serper returned %d unique results.",
            len(results),
        )

        return "\n\n".join(results)