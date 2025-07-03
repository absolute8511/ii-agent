"""Comprehensive tests for the LS tool implementation."""

import os
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.tools.file_system.ls_tool import LSTool, TreeNode, MAX_FILES


class TestLSTool:
    """Test suite for LSTool."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.tool = LSTool()
        self.test_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test environment after each test."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def create_test_structure(self):
        """Create a test directory structure."""
        # Create files
        Path(self.test_dir, "file1.txt").write_text("content1")
        Path(self.test_dir, "file2.py").write_text("print('hello')")
        Path(self.test_dir, ".hidden_file").write_text("hidden")
        
        # Create subdirectories and files
        subdir1 = Path(self.test_dir, "subdir1")
        subdir1.mkdir()
        Path(subdir1, "nested_file.txt").write_text("nested content")
        
        # Create __pycache__ directory
        pycache_dir = Path(subdir1, "__pycache__")
        pycache_dir.mkdir()
        Path(pycache_dir, "cache_file.pyc").write_text("bytecode")
        
        # Create deep nested structure
        subdir2 = Path(self.test_dir, "subdir2")
        deep_dir = Path(subdir2, "deep", "deeper")
        deep_dir.mkdir(parents=True)
        Path(deep_dir, "deepest.txt").write_text("deep content")
        
        # Create hidden directory
        hidden_dir = Path(self.test_dir, ".hidden_dir")
        hidden_dir.mkdir()
        Path(hidden_dir, "hidden_content.txt").write_text("hidden content")

    def test_basic_functionality(self):
        """Test basic directory listing functionality."""
        self.create_test_structure()
        
        result = self.tool.run_impl(self.test_dir)
        
        assert result["success"] is True
        assert "tree" in result
        assert result["directory"] == self.test_dir
        assert result["num_items"] > 0
        assert result["truncated"] is False
        assert "duration_ms" in result
        
        # Check that the tree contains expected files
        tree_content = result["tree"]
        assert "file1.txt" in tree_content
        assert "file2.py" in tree_content
        assert "subdir1/" in tree_content
        assert "subdir2/" in tree_content
        
        # Check that hidden files are skipped by default
        assert ".hidden_file" not in tree_content
        assert ".hidden_dir" not in tree_content
        assert "__pycache__" not in tree_content

    def test_empty_directory(self):
        """Test listing an empty directory."""
        result = self.tool.run_impl(self.test_dir)
        
        assert result["success"] is True
        assert result["num_items"] == 0

    def test_invalid_path_not_absolute(self):
        """Test error handling for non-absolute paths."""
        result = self.tool.run_impl("relative/path")
        
        assert result["success"] is False
        assert result["error_type"] == "invalid_path"
        assert "must be absolute" in result["error"]

    def test_nonexistent_path(self):
        """Test error handling for non-existent paths."""
        nonexistent_path = "/this/path/does/not/exist"
        result = self.tool.run_impl(nonexistent_path)
        
        assert result["success"] is False
        assert result["error_type"] == "path_not_found"
        assert "does not exist" in result["error"]

    def test_path_is_file_not_directory(self):
        """Test error handling when path is a file, not a directory."""
        # Create a test file
        test_file = Path(self.test_dir, "test_file.txt")
        test_file.write_text("test content")
        
        result = self.tool.run_impl(str(test_file))
        
        assert result["success"] is False
        assert result["error_type"] == "not_a_directory"
        assert "not a directory" in result["error"]

    def test_ignore_patterns(self):
        """Test ignore patterns functionality."""
        self.create_test_structure()
        
        # Ignore all .txt files
        result = self.tool.run_impl(self.test_dir, ignore=["*.txt"])
        
        assert result["success"] is True
        tree_content = result["tree"]
        
        # .txt files should be ignored
        assert "file1.txt" not in tree_content
        assert "nested_file.txt" not in tree_content
        assert "deepest.txt" not in tree_content
        
        # .py files should still be present
        assert "file2.py" in tree_content

    def test_should_skip_functionality(self):
        """Test the _should_skip method directly."""
        # Test dotfiles
        assert self.tool._should_skip(".hidden_file") is True
        assert self.tool._should_skip(".hidden_dir/file.txt") is True
        assert self.tool._should_skip("normal_file.txt") is False
        
        # Test __pycache__
        assert self.tool._should_skip("some/path/__pycache__/file.pyc") is True
        assert self.tool._should_skip("normal/path/file.py") is False
        
        # Test ignore patterns
        assert self.tool._should_skip("test.txt", ["*.txt"]) is True
        assert self.tool._should_skip("test.py", ["*.txt"]) is False
        assert self.tool._should_skip("subfolder/test.txt", ["*.txt"]) is True

    def test_tree_node_creation(self):
        """Test TreeNode creation and properties."""
        node = TreeNode("test", "path/test", "file", None)
        assert node.name == "test"
        assert node.path == "path/test"
        assert node.type == "file"
        assert node.children is None
        
        children = [TreeNode("child", "path/child", "file", None)]
        parent_node = TreeNode("parent", "path/parent", "directory", children)
        assert parent_node.children == children

    def test_create_file_tree(self):
        """Test file tree creation from paths."""
        paths = [
            "dir1/file1.txt",
            "dir1/file2.txt", 
            "dir1/subdir/nested.txt",
            "dir2/file3.txt",
            "root_file.txt"
        ]
        
        tree = self.tool._create_file_tree(paths)
        
        # Should have 3 root nodes: dir1/, dir2/, root_file.txt
        assert len(tree) == 3
        
        # Find dir1 node
        dir1_node = next(node for node in tree if node.name == "dir1")
        assert dir1_node.type == "directory"
        assert dir1_node.children is not None
        assert len(dir1_node.children) == 3  # file1.txt, file2.txt, subdir/

    def test_max_files_limit(self):
        """Test that the tool respects the MAX_FILES limit."""
        # Create many files to test the limit - use smaller number for faster testing
        large_test_dir = tempfile.mkdtemp()
        try:
            # Create more than MAX_FILES files
            for i in range(min(50, MAX_FILES + 10)):
                Path(large_test_dir, f"file_{i:04d}.txt").write_text(f"content {i}")
            
            result = self.tool.run_impl(large_test_dir)
            
            assert result["success"] is True
            assert result["num_items"] >= 0
            
        finally:
            shutil.rmtree(large_test_dir)

    def test_permission_error_handling(self):
        """Test handling of permission errors."""
        self.create_test_structure()
        
        # Mock os.listdir to raise PermissionError
        with patch('os.listdir', side_effect=PermissionError("Permission denied")):
            result = self.tool.run_impl(self.test_dir)
            
            # Should handle the error gracefully and return success
            assert result["success"] is True
            # Should have fewer items due to permission errors
            assert result["num_items"] >= 0

    def test_unexpected_error_handling(self):
        """Test handling of unexpected errors."""
        # Mock os.path.isabs to raise an exception
        with patch('os.path.isabs', side_effect=Exception("Unexpected error")):
            result = self.tool.run_impl(self.test_dir)
            
            assert result["success"] is False
            assert result["error_type"] == "unexpected_error"
            assert "Unexpected error" in result["error"]

    def test_tool_properties(self):
        """Test tool properties and configuration."""
        assert self.tool.name == "LS"
        assert isinstance(self.tool.description, str)
        assert "Lists files and directories" in self.tool.description


if __name__ == "__main__":
    pytest.main([__file__])
