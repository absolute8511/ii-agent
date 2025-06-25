"""Utilities for translating between MCP and LLMTool schemas."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def translate_mcp_schema_to_llm_tool(mcp_tool_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Translate MCP tool schema to LLMTool input schema format.
    
    Args:
        mcp_tool_schema: MCP tool schema following MCP specification
        
    Returns:
        LLMTool compatible input schema
    """
    try:
        # Extract basic information
        name = mcp_tool_schema.get("name", "")
        description = mcp_tool_schema.get("description", "")
        input_schema = mcp_tool_schema.get("inputSchema", {})
        
        # MCP schemas are typically JSON Schema format, which is compatible with LLMTool
        # We may need to do some minor adjustments
        
        # Ensure we have the basic structure
        if not isinstance(input_schema, dict):
            logger.warning(f"Invalid input schema for MCP tool {name}, using empty object")
            input_schema = {"type": "object", "properties": {}}
        
        # Ensure schema has required fields
        if "type" not in input_schema:
            input_schema["type"] = "object"
        
        if "properties" not in input_schema and input_schema["type"] == "object":
            input_schema["properties"] = {}
        
        # Handle common MCP-specific schema extensions
        llm_schema = _normalize_schema(input_schema)
        
        logger.debug(f"Translated MCP tool schema for {name}: {llm_schema}")
        
        return llm_schema
        
    except Exception as e:
        logger.error(f"Error translating MCP schema: {str(e)}")
        # Return a basic schema as fallback
        return {
            "type": "object",
            "properties": {},
            "required": []
        }


def _normalize_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a JSON schema for LLMTool compatibility.
    
    Args:
        schema: JSON schema to normalize
        
    Returns:
        Normalized schema
    """
    normalized = schema.copy()
    
    # Handle different schema types
    if normalized.get("type") == "object":
        # Ensure properties exist
        if "properties" not in normalized:
            normalized["properties"] = {}
        
        # Recursively normalize properties
        for prop_name, prop_schema in normalized["properties"].items():
            if isinstance(prop_schema, dict):
                normalized["properties"][prop_name] = _normalize_schema(prop_schema)
    
    elif normalized.get("type") == "array":
        # Normalize array items
        if "items" in normalized and isinstance(normalized["items"], dict):
            normalized["items"] = _normalize_schema(normalized["items"])
    
    # Handle oneOf, anyOf, allOf
    for key in ["oneOf", "anyOf", "allOf"]:
        if key in normalized and isinstance(normalized[key], list):
            normalized[key] = [_normalize_schema(item) if isinstance(item, dict) else item 
                             for item in normalized[key]]
    
    # Remove unsupported extensions or convert them
    _clean_unsupported_features(normalized)
    
    return normalized


def _clean_unsupported_features(schema: Dict[str, Any]):
    """Remove or convert unsupported schema features.
    
    Args:
        schema: Schema to clean (modified in place)
    """
    # List of potentially unsupported features to remove
    unsupported_keys = [
        "$schema",
        "$id",
        "$ref",  # We don't support references for now
        "definitions",
        "$defs"
    ]
    
    for key in unsupported_keys:
        schema.pop(key, None)
    
    # Convert some features to supported alternatives
    if "const" in schema:
        # Convert const to enum with single value
        const_value = schema.pop("const")
        schema["enum"] = [const_value]
    
    # Ensure enum values are JSON serializable
    if "enum" in schema:
        try:
            import json
            json.dumps(schema["enum"])
        except (TypeError, ValueError):
            logger.warning("Non-serializable enum values detected, removing enum constraint")
            schema.pop("enum", None)


def translate_llm_tool_result_to_mcp(result: Any) -> List[Dict[str, Any]]:
    """Translate LLMTool result to MCP format.
    
    Args:
        result: Result from LLMTool execution
        
    Returns:
        MCP-formatted result content
    """
    try:
        if isinstance(result, str):
            # Simple text result
            return [{
                "type": "text",
                "text": result
            }]
        elif isinstance(result, list):
            # Already in structured format, validate and return
            mcp_content = []
            for item in result:
                if isinstance(item, dict):
                    mcp_content.append(_normalize_content_item(item))
                else:
                    mcp_content.append({
                        "type": "text",
                        "text": str(item)
                    })
            return mcp_content
        elif isinstance(result, dict):
            # Single structured item
            return [_normalize_content_item(result)]
        else:
            # Convert to string
            return [{
                "type": "text",
                "text": str(result)
            }]
            
    except Exception as e:
        logger.error(f"Error translating result to MCP format: {str(e)}")
        return [{
            "type": "text",
            "text": f"Error formatting result: {str(e)}"
        }]


def _normalize_content_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a content item to MCP format.
    
    Args:
        item: Content item to normalize
        
    Returns:
        MCP-formatted content item
    """
    # Handle different content types
    if "type" in item:
        content_type = item["type"]
        
        if content_type == "text":
            return {
                "type": "text",
                "text": item.get("text", "")
            }
        elif content_type == "image":
            return {
                "type": "image",
                "data": item.get("data", ""),
                "mimeType": item.get("mimeType", "image/png")
            }
        elif content_type == "resource":
            return {
                "type": "resource",
                "resource": {
                    "uri": item.get("uri", ""),
                    "text": item.get("text", ""),
                    "mimeType": item.get("mimeType", "text/plain")
                }
            }
        else:
            # Unknown type, treat as text
            return {
                "type": "text",
                "text": str(item)
            }
    else:
        # No type specified, treat as text
        return {
            "type": "text",
            "text": str(item)
        }


def validate_mcp_tool_schema(schema: Dict[str, Any]) -> bool:
    """Validate that a schema is a valid MCP tool schema.
    
    Args:
        schema: Schema to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Check required fields
        if not isinstance(schema, dict):
            return False
        
        required_fields = ["name", "description"]
        for field in required_fields:
            if field not in schema or not isinstance(schema[field], str):
                logger.error(f"Missing or invalid required field: {field}")
                return False
        
        # Check input schema if present
        if "inputSchema" in schema:
            input_schema = schema["inputSchema"]
            if not isinstance(input_schema, dict):
                logger.error("inputSchema must be a dictionary")
                return False
            
            # Basic JSON Schema validation
            if "type" in input_schema and input_schema["type"] not in [
                "object", "array", "string", "number", "integer", "boolean", "null"
            ]:
                logger.error(f"Invalid schema type: {input_schema['type']}")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating MCP tool schema: {str(e)}")
        return False


def get_schema_summary(schema: Dict[str, Any]) -> str:
    """Get a human-readable summary of a schema.
    
    Args:
        schema: Schema to summarize
        
    Returns:
        Human-readable summary
    """
    try:
        if not isinstance(schema, dict):
            return "Invalid schema"
        
        schema_type = schema.get("type", "unknown")
        
        if schema_type == "object":
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            
            if not properties:
                return "Empty object"
            
            prop_summary = []
            for prop_name, prop_schema in properties.items():
                prop_type = prop_schema.get("type", "unknown") if isinstance(prop_schema, dict) else "unknown"
                is_required = prop_name in required
                req_indicator = "*" if is_required else ""
                prop_summary.append(f"{prop_name}{req_indicator}: {prop_type}")
            
            return f"Object with {len(properties)} properties: {', '.join(prop_summary)}"
        
        elif schema_type == "array":
            items_schema = schema.get("items", {})
            if isinstance(items_schema, dict):
                items_type = items_schema.get("type", "unknown")
                return f"Array of {items_type}"
            else:
                return "Array"
        
        else:
            return f"Type: {schema_type}"
            
    except Exception as e:
        logger.error(f"Error generating schema summary: {str(e)}")
        return "Error generating summary"