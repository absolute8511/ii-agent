#!/usr/bin/env python3
"""Comprehensive test suite for the BashTool implementation."""

import os
import sys
import tempfile
import time
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, 'src')

from tools.bash.bash_tool import BashTool, BashToolResult, format_output, split_commands, TimeoutProcess, BANNED_COMMANDS
from tools.constants import MAX_OUTPUT_CHARS, DEFAULT_TIMEOUT_MS, MAX_TIMEOUT_MS


class TestBashTool:
    """Test suite for BashTool class."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        self.bash_tool = BashTool()
    
    def test_tool_basic_properties(self):
        """Test basic tool properties."""
        assert self.bash_tool.name == "Bash"
        assert "bash command" in self.bash_tool.description.lower()
        assert "persistent shell session" in self.bash_tool.description
    
    def test_simple_command_execution(self):
        """Test execution of simple commands."""
        result = self.bash_tool.run_impl("echo 'Hello World'")
        
        assert result["exit_code"] == 0
        assert "Hello World" in result["stdout"]
        assert result["stderr"] == ""
        assert not result["interrupted"]
        assert result["stdout_lines"] > 0
    
    def test_command_with_exit_code(self):
        """Test command that returns non-zero exit code."""
        result = self.bash_tool.run_impl("exit 42")
        
        assert result["exit_code"] == 42
        assert "Exit code 42" in result["stderr"]
        assert not result["interrupted"]
    
    def test_command_with_stderr(self):
        """Test command that produces stderr output."""
        result = self.bash_tool.run_impl("echo 'error message' >&2")
        
        assert result["exit_code"] == 0
        assert "error message" in result["stderr"]
        assert result["stdout"] == ""
    
    def test_command_with_both_outputs(self):
        """Test command that produces both stdout and stderr."""
        result = self.bash_tool.run_impl("echo 'stdout'; echo 'stderr' >&2")
        
        assert result["exit_code"] == 0
        assert "stdout" in result["stdout"]
        assert "stderr" in result["stderr"]
    
    def test_banned_command_validation(self):
        """Test that banned commands are rejected."""
        for banned_cmd in BANNED_COMMANDS:
            result = self.bash_tool.run_impl(banned_cmd)
            
            assert result["exit_code"] == 1
            assert "not allowed for security reasons" in result["stderr"]
            assert result["stdout"] == ""
    
    def test_banned_command_with_arguments(self):
        """Test that banned commands with arguments are rejected."""
        result = self.bash_tool.run_impl("curl -v google.com")
        
        assert result["exit_code"] == 1
        assert "not allowed for security reasons" in result["stderr"]
    
    def test_invalid_command_syntax(self):
        """Test handling of invalid command syntax."""
        result = self.bash_tool.run_impl("echo 'unclosed quote")
        
        assert result["exit_code"] == 1
        assert "Invalid command syntax" in result["stderr"]
    
    def test_multiple_commands_with_semicolon(self):
        """Test execution of multiple commands separated by semicolon."""
        result = self.bash_tool.run_impl("echo 'first'; echo 'second'")
        
        assert result["exit_code"] == 0
        assert "first" in result["stdout"]
        assert "second" in result["stdout"]
    
    def test_multiple_commands_with_and(self):
        """Test execution of multiple commands separated by &&."""
        result = self.bash_tool.run_impl("echo 'first' && echo 'second'")
        
        assert result["exit_code"] == 0
        assert "first" in result["stdout"]
        assert "second" in result["stdout"]
    
    def test_multiple_commands_with_failure(self):
        """Test multiple commands where one fails."""
        result = self.bash_tool.run_impl("echo 'success' && exit 1")
        
        assert result["exit_code"] == 1
        assert "success" in result["stdout"]
        assert "Exit code 1" in result["stderr"]
    
    def test_timeout_validation(self):
        """Test timeout parameter validation."""
        result = self.bash_tool.run_impl("echo 'test'", timeout=MAX_TIMEOUT_MS + 1)
        
        assert result["exit_code"] == 1
        assert "cannot exceed" in result["stderr"]
    
    def test_custom_timeout_success(self):
        """Test command execution with custom timeout (success case)."""
        result = self.bash_tool.run_impl("echo 'quick command'", timeout=5000)
        
        assert result["exit_code"] == 0
        assert "quick command" in result["stdout"]
        assert not result["interrupted"]
    
    def test_working_directory_commands(self):
        """Test commands that depend on working directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test content")
            
            # Change to temp directory and list files
            result = self.bash_tool.run_impl(f"cd {tmpdir} && ls")
            
            assert result["exit_code"] == 0
            assert "test.txt" in result["stdout"]
    
    def test_description_parameter(self):
        """Test that description parameter is included in result."""
        description = "List files in directory"
        result = self.bash_tool.run_impl("ls", description=description)
        
        assert result["description"] == description
    
    def test_default_description(self):
        """Test that default description is used when none provided."""
        result = self.bash_tool.run_impl("echo 'test'")
        
        assert "bash command" in result["description"].lower()
    
    def test_file_operations(self):
        """Test file creation and manipulation commands."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.txt")
            
            # Create file
            result = self.bash_tool.run_impl(f"echo 'test content' > {test_file}")
            assert result["exit_code"] == 0
            
            # Read file
            result = self.bash_tool.run_impl(f"cat {test_file}")
            assert result["exit_code"] == 0
            assert "test content" in result["stdout"]
    
    def test_environment_variables(self):
        """Test commands with environment variables."""
        result = self.bash_tool.run_impl("export TEST_VAR='hello' && echo $TEST_VAR")
        
        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]
    
    def test_quoted_paths_with_spaces(self):
        """Test handling of quoted paths with spaces."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create directory with spaces
            space_dir = os.path.join(tmpdir, "dir with spaces")
            os.makedirs(space_dir)
            
            result = self.bash_tool.run_impl(f'ls "{space_dir}"')
            assert result["exit_code"] == 0


class TestBashToolResult:
    """Test suite for BashToolResult class."""
    
    def test_basic_result_creation(self):
        """Test basic result object creation."""
        result = BashToolResult("stdout", "stderr", 0)
        
        assert result.stdout == "stdout"
        assert result.stderr == "stderr"
        assert result.exit_code == 0
        assert not result.interrupted
        assert result.stdout_lines == 1
        assert result.stderr_lines == 1
    
    def test_result_with_multiline_output(self):
        """Test result with multiline output."""
        stdout = "line1\nline2\nline3"
        stderr = "error1\nerror2"
        
        result = BashToolResult(stdout, stderr, 1, interrupted=True)
        
        assert result.stdout_lines == 3
        assert result.stderr_lines == 2
        assert result.interrupted
    
    def test_result_with_empty_output(self):
        """Test result with empty output."""
        result = BashToolResult("", "", 0)
        
        assert result.stdout_lines == 0
        assert result.stderr_lines == 0


class TestFormatOutput:
    """Test suite for format_output function."""
    
    def test_short_output_no_truncation(self):
        """Test that short output is not truncated."""
        content = "Short content"
        formatted, lines = format_output(content)
        
        assert formatted == content
        assert lines == 1
    
    def test_long_output_truncation(self):
        """Test that long output is properly truncated."""
        # Create content longer than MAX_OUTPUT_CHARS
        long_content = "A" * (MAX_OUTPUT_CHARS + 1000)
        formatted, lines = format_output(long_content)
        
        assert len(formatted) < len(long_content)
        assert "truncated" in formatted
        assert lines == 1  # Single long line
    
    def test_multiline_output_line_counting(self):
        """Test proper line counting in multiline output."""
        content = "line1\nline2\nline3\nline4"
        formatted, lines = format_output(content)
        
        assert formatted == content  # Should not be truncated
        assert lines == 4
    
    def test_truncation_preserves_start_and_end(self):
        """Test that truncation preserves both start and end of content."""
        # Create long content with identifiable start and end
        start_marker = "START_MARKER"
        end_marker = "END_MARKER"
        middle_content = "X" * MAX_OUTPUT_CHARS
        long_content = start_marker + middle_content + end_marker
        
        formatted, lines = format_output(long_content)
        
        assert start_marker in formatted
        assert end_marker in formatted
        assert "truncated" in formatted


class TestSplitCommands:
    """Test suite for split_commands function."""
    
    def test_single_command(self):
        """Test splitting single command."""
        commands = split_commands("echo hello")
        assert commands == ["echo hello"]
    
    def test_multiple_commands_semicolon(self):
        """Test splitting commands separated by semicolon."""
        commands = split_commands("echo hello; echo world")
        assert commands == ["echo hello", "echo world"]
    
    def test_multiple_commands_and(self):
        """Test splitting commands separated by &&."""
        commands = split_commands("echo hello && echo world")
        assert commands == ["echo hello", "echo world"]
    
    def test_commands_with_quotes(self):
        """Test splitting commands with quoted strings."""
        commands = split_commands('echo "hello; world" && echo test')
        assert commands == ['echo "hello; world"', "echo test"]
    
    def test_commands_with_single_quotes(self):
        """Test splitting commands with single quoted strings."""
        commands = split_commands("echo 'hello && world'; echo test")
        assert commands == ["echo 'hello && world'", "echo test"]
    
    def test_mixed_separators(self):
        """Test commands with mixed separators."""
        commands = split_commands("echo first; echo second && echo third")
        assert commands == ["echo first", "echo second", "echo third"]
    
    def test_empty_commands_filtered(self):
        """Test that empty commands are filtered out."""
        commands = split_commands("echo hello;; echo world")
        assert commands == ["echo hello", "echo world"]

    def test_commands_with_pipes(self):
        """Test splitting commands with pipes."""
        commands = split_commands("echo hello | grep world")
        assert commands == ["echo hello", "grep world"]

    def test_commands_with_mixed_operators(self):
        """Test splitting commands with mixed operators."""
        commands = split_commands("echo first && echo second | grep test; echo third")
        assert commands == ["echo first", "echo second", "grep test", "echo third"]


class TestTimeoutProcess:
    """Test suite for TimeoutProcess class."""
    
    def test_quick_command_no_timeout(self):
        """Test quick command that completes before timeout."""
        processor = TimeoutProcess("echo 'quick'", 5000)
        result = processor.execute()
        
        assert result.exit_code == 0
        assert "quick" in result.stdout
        assert not result.interrupted
    
    def test_command_timeout(self):
        """Test command that times out."""
        # Use a command that sleeps for longer than timeout
        processor = TimeoutProcess("sleep 2", 100)  # 100ms timeout
        result = processor.execute()
        
        assert result.interrupted
        assert "timed out" in result.stderr
        # Exit code varies by system: -15 on Linux, 143 on others
        assert result.exit_code in [-15, 143]  # SIGTERM exit code varies by system
    
    def test_custom_working_directory(self):
        """Test command execution in custom working directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = TimeoutProcess("pwd", 5000, cwd=tmpdir)
            result = processor.execute()
            
            assert result.exit_code == 0
            assert tmpdir in result.stdout
    
    def test_command_with_error(self):
        """Test command that produces an error."""
        processor = TimeoutProcess("nonexistent_command_12345", 5000)
        result = processor.execute()
        
        assert result.exit_code != 0
        assert result.stderr != ""


class TestIntegrationScenarios:
    """Integration tests for realistic usage scenarios."""
    
    def setup_method(self):
        """Set up test environment."""
        self.bash_tool = BashTool()
    
    def test_git_workflow_simulation(self):
        """Test a simulated git workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize git repo
            result = self.bash_tool.run_impl(f"cd {tmpdir} && git init")
            if result["exit_code"] != 0:
                pytest.skip("Git not available")
            
            # Configure git
            self.bash_tool.run_impl(f"cd {tmpdir} && git config user.email 'test@example.com'")
            self.bash_tool.run_impl(f"cd {tmpdir} && git config user.name 'Test User'")
            
            # Create and add file
            result = self.bash_tool.run_impl(f"cd {tmpdir} && echo 'test' > test.txt && git add test.txt")
            assert result["exit_code"] == 0
            
            # Check status
            result = self.bash_tool.run_impl(f"cd {tmpdir} && git status")
            assert result["exit_code"] == 0
            assert "test.txt" in result["stdout"]
    
    def test_python_script_execution(self):
        """Test execution of Python scripts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            script_file = os.path.join(tmpdir, "test_script.py")
            
            # Create Python script
            script_content = """
print("Hello from Python")
import sys
print(f"Python version: {sys.version.split()[0]}")
"""
            with open(script_file, 'w') as f:
                f.write(script_content)
            
            # Execute script
            result = self.bash_tool.run_impl(f"python {script_file}")
            
            assert result["exit_code"] == 0
            assert "Hello from Python" in result["stdout"]
            assert "Python version:" in result["stdout"]
    
    def test_file_processing_pipeline(self):
        """Test a file processing pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = os.path.join(tmpdir, "input.txt")
            output_file = os.path.join(tmpdir, "output.txt")
            
            # Create input file
            with open(input_file, 'w') as f:
                f.write("apple\nbanana\ncherry\napricot\nblueberry")
            
            # Process file: sort and filter lines starting with 'a'
            result = self.bash_tool.run_impl(
                f"cat {input_file} | sort | grep '^a' > {output_file}"
            )
            
            assert result["exit_code"] == 0
            
            # Verify output
            result = self.bash_tool.run_impl(f"cat {output_file}")
            assert result["exit_code"] == 0
            assert "apple" in result["stdout"]
            assert "apricot" in result["stdout"]
            assert "banana" not in result["stdout"]
    
    def test_network_command_blocking(self):
        """Test that network commands are properly blocked."""
        network_commands = [
            "curl google.com",
            "wget https://example.com",
            "nc -l 8080",
            "telnet example.com 80"
        ]
        
        for cmd in network_commands:
            result = self.bash_tool.run_impl(cmd)
            assert result["exit_code"] == 1
            assert "not allowed for security reasons" in result["stderr"]
    
    def test_large_output_handling(self):
        """Test handling of commands that produce large output."""
        # Generate large output
        result = self.bash_tool.run_impl("seq 1 10000")
        
        assert result["exit_code"] == 0
        # seq 1 10000 produces 10000 numbers + final newline = 10001 lines
        assert result["stdout_lines"] == 10001
        
        # If output is truncated, it should contain truncation notice
        if len(result["stdout"]) < len("1\n2\n" * 10000):
            assert "truncated" in result["stdout"]


class TestSecurityFeatures:
    """Test suite for security features."""
    
    def setup_method(self):
        """Set up test environment."""
        self.bash_tool = BashTool()
    
    def test_command_injection_basic_protection(self):
        """Test basic protection against command injection."""
        # Test various injection patterns
        injection_attempts = [
            "echo hello; rm -rf /",
            "echo hello && curl evil.com",
            "echo 'safe' | wget badsite.com"
        ]
        
        for cmd in injection_attempts:
            result = self.bash_tool.run_impl(cmd)
            # Should block the dangerous command
            assert result["exit_code"] == 1
            assert "not allowed" in result["stderr"]
    
    def test_all_banned_commands_blocked(self):
        """Test that all banned commands are properly blocked."""
        for banned_cmd in BANNED_COMMANDS:
            result = self.bash_tool.run_impl(banned_cmd)
            assert result["exit_code"] == 1
            assert "not allowed for security reasons" in result["stderr"]
    
    def test_case_insensitive_blocking(self):
        """Test that banned commands are blocked regardless of case."""
        result = self.bash_tool.run_impl("CURL google.com")
        assert result["exit_code"] == 1
        assert "not allowed for security reasons" in result["stderr"]
        
        result = self.bash_tool.run_impl("Wget example.com")
        assert result["exit_code"] == 1
        assert "not allowed for security reasons" in result["stderr"]


def test_module_imports():
    """Test that all required modules can be imported."""
    from tools.bash.bash_tool import BashTool, BashToolResult, format_output, split_commands
    from tools.constants import MAX_OUTPUT_CHARS, DEFAULT_TIMEOUT_MS
    
    assert BashTool is not None
    assert BashToolResult is not None
    assert format_output is not None
    assert split_commands is not None


if __name__ == "__main__":
    # Run specific test if provided as argument
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        pytest.main(["-v", f"test_bash_tool.py::{test_name}"])
    else:
        # Run all tests
        pytest.main(["-v", "test_bash_tool.py"]) 