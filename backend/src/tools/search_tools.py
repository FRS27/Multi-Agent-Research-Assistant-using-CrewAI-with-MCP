import os
import requests
import json
from crewai.tools import BaseTool
from pydantic import Field

class BraveSearchTool(BaseTool):
    name: str = "Brave Search"
    description: str = (
        "Useful for searching the internet to find objective facts, "
        "news, and information on a given topic."
    )
    api_key: str = Field(default_factory=lambda: os.getenv("BRAVE_SEARCH_API_KEY"))

    def _run(self, query: str) -> str:
        """
        Executes a search using the Brave Search API.
        """
        if not self.api_key:
            return "Error: BRAVE_SEARCH_API_KEY is missing in the environment variables."

        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key
        }
        params = {"q": query}

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Parse the results to be LLM-friendly
            results = []
            # We take the top 5 results
            for item in data.get("web", {}).get("results", [])[:5]:
                title = item.get("title", "No Title")
                link = item.get("url", "#")
                description = item.get("description", "No description")
                results.append(f"Title: {title}\nLink: {link}\nSnippet: {description}\n---")
            
            return "\n".join(results) if results else "No relevant results found."

        except Exception as e:
            return f"Error performing search: {str(e)}"

# Initialize the tool
search_tool = BraveSearchTool()