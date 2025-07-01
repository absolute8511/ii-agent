"""WebFetch tool for fetching content from URLs."""

from typing import Annotated
from pydantic import Field
from src.tools.base import BaseTool


class WebFetchTool(BaseTool):
    """Tool for fetching and processing web content."""
    
    name = "WebFetch"
    description = """\

- Fetches content from a specified URL and processes it using an AI model
- Takes a URL and a prompt as input
- Fetches the URL content, converts HTML to markdown
- Processes the content with the prompt using a small, fast model
- Returns the model's response about the content
- Use this tool when you need to retrieve and analyze web content

Usage notes:
  - IMPORTANT: If an MCP-provided web fetch tool is available, prefer using that tool instead of this one, as it may have fewer restrictions. All MCP-provided tools start with "mcp__".
  - The URL must be a fully-formed valid URL
  - HTTP URLs will be automatically upgraded to HTTPS
  - The prompt should describe what information you want to extract from the page
  - This tool is read-only and does not modify any files
  - Results may be summarized if the content is very large
  - Includes a self-cleaning 15-minute cache for faster responses when repeatedly accessing the same URL
"""

    def run_impl(
        self,
        url: Annotated[str, Field(description="The URL to fetch content from")],
        prompt: Annotated[str, Field(description="The prompt to run on the fetched content")],
    ) -> str:
        """Fetch content from a URL and process it with the given prompt."""
        # TODO: Implement web fetching logic
        # This would involve:
        # 1. Validating the URL format
        # 2. Making HTTP request with proper headers and timeout
        # 3. Converting HTML to markdown if needed
        # 4. Processing content with AI model using the prompt
        # 5. Implementing caching mechanism
        # 6. Handling various content types and encodings
        # 7. Error handling for network issues, invalid URLs, etc.
        
        return f"Would fetch content from: {url}\nProcess with prompt: {prompt[:100]}...\n[Fetched and processed content would appear here]"