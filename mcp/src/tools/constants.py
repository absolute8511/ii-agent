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

# Web search constants
MIN_QUERY_LENGTH = 2
WEB_SEARCH_US_ONLY = True

# Agent tool constants
AGENT_AVAILABLE_TOOLS = [
    'Bash', 'Glob', 'Grep', 'LS', 'exit_plan_mode', 'Read', 'Edit', 
    'MultiEdit', 'Write', 'NotebookRead', 'NotebookEdit', 'WebFetch', 
    'TodoRead', 'TodoWrite', 'WebSearch', 'mcp__ide__getDiagnostics', 
    'mcp__ide__executeCode'
]

# Todo management constants
TODO_STATES = ['pending', 'in_progress', 'completed']
TODO_PRIORITIES = ['high', 'medium', 'low']
MAX_TODOS_IN_PROGRESS = 1