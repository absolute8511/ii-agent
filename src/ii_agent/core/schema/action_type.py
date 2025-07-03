from enum import Enum


class ActionType(str, Enum):
    """Enumeration of all action types supported by ii-agent."""
    
    # Core communication actions
    MESSAGE = "message"
    """Represents a message from agent to user."""
    
    # File operations
    READ = "read"
    """Reads the content of a file."""
    
    WRITE = "write" 
    """Writes content to a file."""
    
    EDIT = "edit"
    """Edits a file using various commands."""
    
    # Command execution
    RUN = "run"
    """Runs a shell command."""
    
    RUN_IPYTHON = "run_ipython"
    """Runs a Python/IPython cell."""
    
    # Browser operations
    BROWSE = "browse"
    """Opens a web page."""
    
    BROWSE_INTERACTIVE = "browse_interactive"
    """Interact with browser elements."""
    
    # Tool operations (backward compatibility)
    TOOL_CALL = "tool_call"
    """Generic tool call action (legacy)."""
    
    # Agent control
    THINK = "think"
    """Logs a thought or reasoning step."""
    
    FINISH = "finish"
    """Indicates task completion."""
    
    REJECT = "reject"
    """Indicates task rejection or failure."""
    
    DELEGATE = "delegate"
    """Delegates a task to another agent."""
    
    # Advanced operations
    RECALL = "recall"
    """Retrieves content from memory or workspace."""
    
    # System control
    PAUSE = "pause"
    """Pauses the current task."""
    
    RESUME = "resume" 
    """Resumes a paused task."""
    
    STOP = "stop"
    """Stops the current task."""