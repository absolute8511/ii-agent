"""Constants for tool configurations matching Claude Code specifications."""

# File system constants
MAX_FILES_LS = 1000
MAX_FILE_READ_LINES = 2000
MAX_LINE_LENGTH = 2000
DEFAULT_TIMEOUT_MS = 120000  # 2 minutes
MAX_TIMEOUT_MS = 600000  # 10 minutes
MAX_OUTPUT_CHARS = 30000

# Search constants
MAX_SEARCH_FILES = 1000
MAX_MATCHES_PER_FILE = 10
MAX_TOTAL_MATCHES = 100
MAX_GLOB_RESULTS = 100

# Notebook constants
NOTEBOOK_EXTENSIONS = ['.ipynb']
SUPPORTED_CELL_TYPES = ['code', 'markdown', 'raw']
EDIT_MODES = ['replace', 'insert', 'delete']

# Binary file extensions to skip in searches
BINARY_EXTENSIONS = {
    '.exe', '.bin', '.dll', '.so', '.dylib', '.class', '.jar', '.war',
    '.zip', '.tar', '.gz', '.7z', '.rar', '.pdf', '.doc', '.docx',
    '.xls', '.xlsx', '.ppt', '.pptx', '.jpg', '.jpeg', '.png', '.gif',
    '.bmp', '.ico', '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv',
    '.webm', '.mkv'
}

# Tool descriptions matching Claude Code exactly
AGENT_TOOL_PROMPT = """Launch a new agent that has access to the following tools: Bash, Glob, Grep, LS, exit_plan_mode, Read, Edit, MultiEdit, Write, NotebookRead, NotebookEdit, WebFetch, TodoRead, TodoWrite, WebSearch, mcp__ide__getDiagnostics, mcp__ide__executeCode. When you are searching for a keyword or file and are not confident that you will find the right match in the first few tries, use the Agent tool to perform the search for you.

When to use the Agent tool:
- If you are searching for a keyword like "config" or "logger", or for questions like "which file does X?", the Agent tool is strongly recommended

When NOT to use the Agent tool:
- If you want to read a specific file path, use the Read or Glob tool instead of the Agent tool, to find the match more quickly
- If you are searching for a specific class definition like "class Foo", use the Glob tool instead, to find the match more quickly
- If you are searching for code within a specific file or set of 2-3 files, use the Read tool instead of the Agent tool, to find the match more quickly
- Writing code and running bash commands (use other tools for that)
- Other tasks that are not related to searching for a keyword or file

Usage notes:
1. Launch multiple agents concurrently whenever possible, to maximize performance; to do that, use a single message with multiple tool uses
2. When the agent is done, it will return a single message back to you. The result returned by the agent is not visible to the user. To show the user the result, you should send a text message back to the user with a concise summary of the result.
3. Each agent invocation is stateless. You will not be able to send additional messages to the agent, nor will the agent be able to communicate with you outside of its final report. Therefore, your prompt should contain a highly detailed task description for the agent to perform autonomously and you should specify exactly what information the agent should return back to you in its final and only message to you.
4. The agent's outputs should generally be trusted
5. Clearly tell the agent whether you expect it to write code or just to do research (search, file reads, web fetches, etc.), since it is not aware of the user's intent"""

# Product name placeholder for bash tool
PRODUCT_NAME = "${PRODUCT_NAME}"

# Git commit template
GIT_COMMIT_TEMPLATE = """🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"""

# Pull request template
PR_BODY_TEMPLATE = """## Summary
{summary}

## Test plan
{test_plan}

🤖 Generated with [Claude Code](https://claude.ai/code)"""

# LS tool truncation message
LS_TRUNCATED_MESSAGE = f"There are more than {MAX_FILES_LS} files in the repository. Use the LS tool (passing a specific path), Bash tool, and other tools to explore nested directories. The first {MAX_FILES_LS} files and directories are included below:\n\n"