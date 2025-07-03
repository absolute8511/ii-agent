"""FastAPI server for Claude Code operations in sandbox environment."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from claude_code_sdk import ClaudeCodeOptions, query
    CLAUDE_CODE_AVAILABLE = True
except ImportError:
    CLAUDE_CODE_AVAILABLE = False
    ClaudeCodeOptions = None
    query = None

logger = logging.getLogger(__name__)


class ClaudeCodeRequest(BaseModel):
    """Request model for Claude Code execution."""
    task: str
    options: Dict[str, Any]


class ClaudeCodeResponse(BaseModel):
    """Response model for Claude Code execution."""
    success: bool
    messages: Optional[List[Any]] = None
    error: Optional[str] = None


class ClaudeCodeServer:
    """Claude Code server for handling remote requests."""

    def __init__(self, cwd: Optional[str] = None):
        self.cwd = cwd or "/workspace"
        
        if not CLAUDE_CODE_AVAILABLE:
            logger.warning("claude_code_sdk not available in this environment")
        
        self.app = FastAPI(
            title="Claude Code Server",
            description="HTTP API for Claude Code operations",
            version="1.0.0",
        )
        
        self._setup_routes()

    def _setup_routes(self):
        """Setup API routes."""

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "ok",
                "claude_code_available": CLAUDE_CODE_AVAILABLE,
                "cwd": self.cwd,
            }

        @self.app.post("/execute", response_model=ClaudeCodeResponse)
        async def execute_claude_code(request: ClaudeCodeRequest):
            """Execute a Claude Code task."""
            if not CLAUDE_CODE_AVAILABLE:
                raise HTTPException(
                    status_code=503,
                    detail="Claude Code SDK is not available in this environment"
                )
            
            try:
                # Set default cwd if not provided in options
                if "cwd" not in request.options:
                    request.options["cwd"] = self.cwd
                
                logger.info(f"Executing Claude Code task: {request.task[:100]}...")
                
                # Convert options to ClaudeCodeOptions
                claude_options = ClaudeCodeOptions(**request.options)
                
                # Execute Claude Code
                messages = []
                async for message in query(prompt=request.task, options=claude_options):
                    # Convert message to serializable format
                    if hasattr(message, '__dict__'):
                        message_dict = {
                            "result": getattr(message, 'result', str(message)),
                            "content": str(message),
                        }
                    else:
                        message_dict = {"result": str(message), "content": str(message)}
                    
                    messages.append(message_dict)
                
                logger.info(f"Claude Code task completed with {len(messages)} messages")
                
                return ClaudeCodeResponse(
                    success=True,
                    messages=messages
                )
                
            except Exception as e:
                logger.error(f"Claude Code execution error: {e}", exc_info=True)
                return ClaudeCodeResponse(
                    success=False,
                    error=str(e)
                )


def create_app(
    cwd: Optional[str] = None,
    allowed_origins: Optional[List[str]] = None,
) -> FastAPI:
    """Factory function to create Claude Code FastAPI app."""
    
    server = ClaudeCodeServer(cwd=cwd)
    app = server.app
    
    # Add CORS middleware
    if allowed_origins is None:
        allowed_origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app


def main():
    """Main entry point for running the Claude Code server standalone."""
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="Claude Code Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8003, help="Port to bind to")
    parser.add_argument("--cwd", default="/workspace", help="Working directory")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create app
    app = create_app(cwd=args.cwd)

    logger.info(f"Starting Claude Code Server on {args.host}:{args.port}")
    logger.info(f"Working directory: {args.cwd}")
    logger.info(f"Claude Code available: {CLAUDE_CODE_AVAILABLE}")
    
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()