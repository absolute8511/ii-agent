from enum import Enum


class ObservationType(str, Enum):
    """Enumeration of all observation types returned by the environment."""
    
    # File operation results
    READ = "read"
    """File read operation result."""
    
    WRITE = "write"
    """File write operation result."""
    
    EDIT = "edit"
    """File edit operation result."""
    
    # Command execution results
    RUN = "run"
    """Shell command execution result."""
    
    RUN_IPYTHON = "run_ipython"
    """Python/IPython execution result."""
    
    # Browser operation results
    BROWSE = "browse"
    """Web page browsing result."""
    
    BROWSE_INTERACTIVE = "browse_interactive"
    """Browser interaction result."""
    
    # Tool operation results (backward compatibility)
    TOOL_RESULT = "tool_result"
    """Generic tool execution result (legacy)."""
    
    # System responses
    ERROR = "error"
    """Error observation."""
    
    SUCCESS = "success"
    """Success observation."""
    
    USER_MESSAGE = "user_message"
    """User message observation."""
    
    SYSTEM = "system"
    """System message observation."""
    
    # Advanced results
    RECALL = "recall"
    """Memory/workspace recall result."""
    
    DELEGATE = "delegate"
    """Task delegation result."""