"""Test the productivity tools implementation."""

import os
import sys
import uuid

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.tools.productivity.todo_read_tool import TodoReadTool
from src.tools.productivity.todo_write_tool import TodoWriteTool
from src.tools.productivity.shared_state import get_todo_manager


def test_todo_tools():
    """Test the todo read and write tools."""
    # Clear any existing todos
    manager = get_todo_manager()
    manager.clear_todos()
    
    # Initialize tools
    read_tool = TodoReadTool()
    write_tool = TodoWriteTool()
    
    # Test reading empty todo list
    print("Test 1: Reading empty todo list")
    result = read_tool.run_impl()
    assert result == [], f"Expected empty list, got {result}"
    print("✓ Passed")
    
    # Test writing todos
    print("\nTest 2: Writing todo list")
    todos = [
        {
            "id": str(uuid.uuid4()),
            "content": "Implement user authentication",
            "status": "in_progress",
            "priority": "high"
        },
        {
            "id": str(uuid.uuid4()),
            "content": "Write unit tests",
            "status": "pending",
            "priority": "medium"
        },
        {
            "id": str(uuid.uuid4()),
            "content": "Update documentation",
            "status": "pending",
            "priority": "low"
        }
    ]
    
    result = write_tool.run_impl(todos=todos)
    assert result["success"] == True, f"Write failed: {result}"
    assert len(result["todos"]) == 3, f"Expected 3 todos, got {len(result['todos'])}"
    print("✓ Passed")
    
    # Test reading the written todos
    print("\nTest 3: Reading written todos")
    result = read_tool.run_impl()
    assert len(result) == 3, f"Expected 3 todos, got {len(result)}"
    # Check sorting - in_progress should be first
    assert result[0]["status"] == "in_progress", "In-progress task should be first"
    assert result[0]["priority"] == "high", "High priority in-progress task should be first"
    print("✓ Passed")
    
    # Test validation - multiple in_progress tasks
    print("\nTest 4: Testing validation - multiple in_progress tasks")
    invalid_todos = [
        {
            "id": str(uuid.uuid4()),
            "content": "Task 1",
            "status": "in_progress",
            "priority": "high"
        },
        {
            "id": str(uuid.uuid4()),
            "content": "Task 2",
            "status": "in_progress",
            "priority": "medium"
        }
    ]
    
    result = write_tool.run_impl(todos=invalid_todos)
    assert result["success"] == False, "Should fail with multiple in_progress tasks"
    assert "Only one task can be in_progress" in result["error"], f"Wrong error message: {result['error']}"
    print("✓ Passed")
    
    # Test validation - missing required fields
    print("\nTest 5: Testing validation - missing required fields")
    invalid_todos = [
        {
            "id": str(uuid.uuid4()),
            "content": "Task without status",
            "priority": "high"
        }
    ]
    
    result = write_tool.run_impl(todos=invalid_todos)
    assert result["success"] == False, "Should fail with missing status"
    assert "status" in result["error"], f"Wrong error message: {result['error']}"
    print("✓ Passed")
    
    # Test validation - invalid status
    print("\nTest 6: Testing validation - invalid status")
    invalid_todos = [
        {
            "id": str(uuid.uuid4()),
            "content": "Task with invalid status",
            "status": "invalid",
            "priority": "high"
        }
    ]
    
    result = write_tool.run_impl(todos=invalid_todos)
    assert result["success"] == False, "Should fail with invalid status"
    assert "Invalid status" in result["error"], f"Wrong error message: {result['error']}"
    print("✓ Passed")
    
    # Test updating existing todos
    print("\nTest 7: Updating existing todos")
    # Mark first task as completed
    todos[0]["status"] = "completed"
    # Mark second task as in_progress
    todos[1]["status"] = "in_progress"
    
    result = write_tool.run_impl(todos=todos)
    assert result["success"] == True, f"Update failed: {result}"
    
    # Read and verify order
    result = read_tool.run_impl()
    assert result[0]["status"] == "in_progress", "In-progress task should be first after update"
    assert result[0]["content"] == "Write unit tests", "Wrong task is in progress"
    print("✓ Passed")
    
    print("\n✨ All tests passed!")


if __name__ == "__main__":
    test_todo_tools()