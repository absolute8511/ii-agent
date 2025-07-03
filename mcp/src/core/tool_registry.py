"""Tool registry for managing and loading tools."""

import importlib
import inspect
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Type, Union
from dataclasses import dataclass

from src.tools.base import BaseTool
from src.tools.constants import AGENT_AVAILABLE_TOOLS


@dataclass
class ToolDefinition:
    """Definition of a tool for API calls."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    tool_instance: BaseTool


class ToolRegistry:
    """Registry for managing available tools."""
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._loaded = False
    
    def load_tools(self, dangerous_skip_permissions: bool = False) -> None:
        """Load all available tools."""
        if self._loaded:
            return
        
        # Import and register all tools
        tool_modules = {
            "Bash": "src.tools.bash.bash_tool.BashTool",
            "Glob": "src.tools.file_system.glob_tool.GlobTool", 
            "Grep": "src.tools.file_system.grep_tool.GrepTool",
            "LS": "src.tools.file_system.ls_tool.LSTool",
            "Read": "src.tools.file_system.file_read_tool.FileReadTool",
            "Edit": "src.tools.file_system.file_edit_tool.FileEditTool",
            "MultiEdit": "src.tools.file_system.multi_edit_tool.MultiEditTool",
            "Write": "src.tools.file_system.file_write_tool.FileWriteTool",
            "WebFetch": "src.tools.web.web_fetch_tool.WebFetchTool",
            "WebSearch": "src.tools.web.web_search_tool.WebSearchTool",
            "TodoRead": "src.tools.productivity.todo_read_tool.TodoReadTool",
            "TodoWrite": "src.tools.productivity.todo_write_tool.TodoWriteTool",
            "exit_plan_mode": "src.tools.exit_plan_mode_tool.ExitPlanModeTool",
        }
        
        # Filter tools based on permissions
        available_tools = AGENT_AVAILABLE_TOOLS
        if not dangerous_skip_permissions:
            # Remove write tools if permissions are restricted
            restricted_tools = {"Bash", "Edit", "MultiEdit", "Write"}
            available_tools = [tool for tool in available_tools if tool not in restricted_tools]
        
        for tool_name in available_tools:
            if tool_name in tool_modules:
                try:
                    module_path, class_name = tool_modules[tool_name].rsplit(".", 1)
                    module = importlib.import_module(module_path)
                    tool_class = getattr(module, class_name)
                    
                    # Create tool instance
                    tool_instance = tool_class()
                    
                    # Generate input schema from tool's run_impl method
                    input_schema = self._generate_input_schema(tool_instance)
                    
                    # Register the tool
                    tool_def = ToolDefinition(
                        name=tool_instance.name,
                        description=tool_instance.description,
                        input_schema=input_schema,
                        tool_instance=tool_instance
                    )
                    
                    self._tools[tool_instance.name] = tool_def
                    
                except Exception as e:
                    print(f"Failed to load tool {tool_name}: {e}")
        
        self._loaded = True
    
    def _generate_input_schema(self, tool: BaseTool) -> Dict[str, Any]:
        """Generate JSON schema for a tool's input parameters."""
        try:
            # Get the run_impl method signature
            sig = inspect.signature(tool.run_impl)
            
            schema = {
                "type": "object",
                "properties": {},
                "required": []
            }
            
            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue
                
                # Extract type information from annotations
                param_type = param.annotation
                param_schema = {"type": "string"}  # Default to string
                
                # Handle typed annotations
                if hasattr(param_type, "__origin__"):
                    origin = param_type.__origin__
                    if origin is Union:
                        # Handle Optional types
                        args = param_type.__args__
                        if len(args) == 2 and type(None) in args:
                            # This is Optional[T]
                            actual_type = args[0] if args[1] is type(None) else args[1]
                            param_schema = self._type_to_schema(actual_type)
                        else:
                            param_schema = {"type": "string"}  # Fallback for complex unions
                    elif origin is list:
                        param_schema = {
                            "type": "array", 
                            "items": {"type": "string"}
                        }
                    elif origin is dict:
                        param_schema = {"type": "object"}
                else:
                    param_schema = self._type_to_schema(param_type)
                
                # Add description from docstring or annotation if available
                if hasattr(param_type, "__metadata__"):
                    for metadata in param_type.__metadata__:
                        if hasattr(metadata, "description"):
                            param_schema["description"] = metadata.description
                
                schema["properties"][param_name] = param_schema
                
                # Mark as required if no default value
                if param.default is inspect.Parameter.empty:
                    schema["required"].append(param_name)
            
            return schema
            
        except Exception as e:
            # Fallback schema
            return {
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "description": "Tool input"
                    }
                },
                "required": []
            }
    
    def _type_to_schema(self, param_type: Type) -> Dict[str, Any]:
        """Convert Python type to JSON schema."""
        if param_type is str or param_type == str:
            return {"type": "string"}
        elif param_type is int or param_type == int:
            return {"type": "integer"}
        elif param_type is float or param_type == float:
            return {"type": "number"}
        elif param_type is bool or param_type == bool:
            return {"type": "boolean"}
        elif param_type is list or param_type == list:
            return {"type": "array", "items": {"type": "string"}}
        elif param_type is dict or param_type == dict:
            return {"type": "object"}
        else:
            return {"type": "string"}  # Fallback
    
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def get_all_tools(self) -> List[ToolDefinition]:
        """Get all registered tools."""
        return list(self._tools.values())
    
    def get_tools_for_api(self) -> List[Dict[str, Any]]:
        """Get tools formatted for API calls."""
        tools = []
        for tool_def in self._tools.values():
            tools.append({
                "type": "function",
                "function": {
                    "name": tool_def.name,
                    "description": tool_def.description,
                    "parameters": tool_def.input_schema
                }
            })
        return tools
    
    def execute_tool(self, name: str, input_data: Dict[str, Any]) -> Any:
        """Execute a tool with the given input."""
        tool_def = self.get_tool(name)
        if not tool_def:
            raise ValueError(f"Tool '{name}' not found")
        
        try:
            # Call the tool's run_impl method with the input data
            return tool_def.tool_instance.run_impl(**input_data)
        except Exception as e:
            raise RuntimeError(f"Tool '{name}' execution failed: {str(e)}")


# Global registry instance
_global_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def get_agent_tools(dangerous_skip_permissions: bool = False) -> List[ToolDefinition]:
    """Get tools available for agent execution."""
    registry = get_registry()
    registry.load_tools(dangerous_skip_permissions)
    
    # Filter out the Agent tool itself to prevent recursion
    all_tools = registry.get_all_tools()
    return [tool for tool in all_tools if tool.name != "Task"]


def get_tools_for_api(dangerous_skip_permissions: bool = False) -> List[Dict[str, Any]]:
    """Get tools formatted for API calls."""
    tools = get_agent_tools(dangerous_skip_permissions)
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema
            }
        }
        for tool in tools
    ] 