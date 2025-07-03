#!/usr/bin/env python3
"""Demonstration script for the BashTool implementation."""

import sys
import json
import tempfile
import os

# Add the src directory to Python path
sys.path.insert(0, 'src')

from tools.bash.bash_tool import BashTool


def demo_bash_tool():
    """Demonstrate various capabilities of the BashTool."""
    
    print("🔧 BashTool Demonstration")
    print("=" * 50)
    
    tool = BashTool()
    
    print(f"Tool Name: {tool.name}")
    print(f"Description snippet: {tool.description[:100]}...")
    print()
    
    # Test cases to demonstrate
    test_cases = [
        {
            "name": "Simple Echo Command",
            "command": "echo 'Hello from BashTool!'",
            "description": "Display a simple greeting"
        },
        {
            "name": "File Operations",
            "command": "ls -la /tmp | head -5",
            "description": "List files in /tmp directory"
        },
        {
            "name": "System Information", 
            "command": "uname -a",
            "description": "Show system information"
        },
        {
            "name": "Multiple Commands",
            "command": "echo 'First command' && echo 'Second command'",
            "description": "Execute multiple commands in sequence"
        },
        {
            "name": "Environment Variables",
            "command": "export TEST_VAR='Demo Value' && echo $TEST_VAR",
            "description": "Set and display environment variable"
        },
        {
            "name": "Error Handling",
            "command": "nonexistent_command_xyz",
            "description": "Test error handling with invalid command"
        },
        {
            "name": "Security Test - Banned Command",
            "command": "curl google.com",
            "description": "Test security blocking of banned commands"
        },
        {
            "name": "Security Test - Dangerous rm",
            "command": "echo test && rm -rf /",
            "description": "Test security blocking of dangerous operations"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_case['name']}")
        print(f"Command: {test_case['command']}")
        print(f"Purpose: {test_case['description']}")
        print("-" * 40)
        
        try:
            result = tool.run_impl(
                command=test_case['command'],
                description=test_case['description'],
                timeout=5000  # 5 second timeout for demo
            )
            
            print(f"✅ Exit Code: {result['exit_code']}")
            print(f"📤 Stdout Lines: {result['stdout_lines']}")
            print(f"📥 Stderr Lines: {result['stderr_lines']}")
            print(f"⏱️  Interrupted: {result['interrupted']}")
            
            if result['stdout'].strip():
                print(f"📄 Output:\n{result['stdout'][:200]}")
                if len(result['stdout']) > 200:
                    print("... (truncated)")
            
            if result['stderr'].strip():
                print(f"⚠️  Error:\n{result['stderr'][:200]}")
                if len(result['stderr']) > 200:
                    print("... (truncated)")
                    
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 BashTool demonstration completed!")
    print("\nKey Features Demonstrated:")
    print("✓ Command execution with proper output handling")
    print("✓ Security validation and banned command blocking")
    print("✓ Multiple command support (&&, ;, |)")
    print("✓ Error handling and exit code management")
    print("✓ Timeout support")
    print("✓ Output truncation for large results")
    print("✓ Line counting for stdout/stderr")


def demo_file_operations():
    """Demonstrate file operations in a safe temporary directory."""
    
    print("\n" + "=" * 50)
    print("📁 File Operations Demo")
    print("=" * 50)
    
    tool = BashTool()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Working in temporary directory: {tmpdir}")
        
        file_ops = [
            {
                "name": "Create Test File",
                "command": f"echo 'This is a test file' > {tmpdir}/test.txt"
            },
            {
                "name": "List Directory Contents", 
                "command": f"ls -la {tmpdir}"
            },
            {
                "name": "Read File Contents",
                "command": f"cat {tmpdir}/test.txt"
            },
            {
                "name": "Append to File",
                "command": f"echo 'Appended line' >> {tmpdir}/test.txt"
            },
            {
                "name": "Show File Size",
                "command": f"wc -l {tmpdir}/test.txt"
            },
            {
                "name": "Create Directory",
                "command": f"mkdir {tmpdir}/subdir && echo 'Created subdirectory'"
            }
        ]
        
        for op in file_ops:
            print(f"\n🔸 {op['name']}")
            result = tool.run_impl(op['command'])
            
            if result['exit_code'] == 0:
                print(f"✅ Success: {result['stdout'].strip()}")
            else:
                print(f"❌ Failed: {result['stderr'].strip()}")


if __name__ == "__main__":
    demo_bash_tool()
    demo_file_operations() 