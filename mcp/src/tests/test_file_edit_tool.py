#!/usr/bin/env python3
"""Test script for the FileEditTool implementation."""

import os
import sys
import tempfile
import shutil

# Add the src directory to Python path
sys.path.insert(0, 'src')

from tools.file_system.file_edit_tool import FileEditTool
from tools.file_system.file_read_tool import FileReadTool


def test_file_edit_tool():
    """Test the file edit tool with various scenarios."""
    
    # Create a temporary directory for our tests
    test_dir = tempfile.mkdtemp()
    test_file = os.path.join(test_dir, "test.txt")
    
    try:
        print("🧪 Testing FileEditTool implementation...")
        print(f"📁 Test directory: {test_dir}")
        print("")
        
        # Initialize tools
        read_tool = FileReadTool()
        edit_tool = FileEditTool()
        
        print(f"✅ Tools initialized: {read_tool.name}, {edit_tool.name}")
        print("")
        
        # Test 1: Create a new file
        print("📝 Test 1: Creating new file...")
        result = edit_tool.run_impl(
            file_path=test_file,
            old_string="",
            new_string="Hello, World!\nThis is a test file.\nWith multiple lines.",
            replace_all=False
        )
        
        if result.get("success"):
            print("✅ File creation successful")
            print(f"   Message: {result.get('message')}")
        else:
            print("❌ File creation failed")
            print(f"   Error: {result.get('error')}")
            return False
        
        print("")
        
        # Test 2: Read the file
        print("📖 Test 2: Reading the file...")
        result = read_tool.run_impl(file_path=test_file)
        
        if result.get("success"):
            print("✅ File read successful")
            print(f"   Lines read: {result.get('lines_read')}")
            print(f"   Encoding: {result.get('encoding')}")
            print("   Content preview:")
            print("   " + "\n   ".join(result.get('content', '').split('\n')[:3]) + "...")
        else:
            print("❌ File read failed")
            print(f"   Error: {result.get('error')}")
            return False
        
        print("")
        
        # Test 3: Edit the file (replace single occurrence)
        print("📝 Test 3: Editing file (single replacement)...")
        result = edit_tool.run_impl(
            file_path=test_file,
            old_string="Hello, World!",
            new_string="Hello, Python!",
            replace_all=False
        )
        
        if result.get("success"):
            print("✅ File edit successful")
            print(f"   Operation: {result.get('operation')}")
            print(f"   Matches replaced: {result.get('matches_replaced')}")
        else:
            print("❌ File edit failed")
            print(f"   Error: {result.get('error')}")
            return False
        
        print("")
        
        # Test 4: Try to edit without reading (should fail)
        print("🚫 Test 4: Attempting edit without reading (should fail)...")
        # Create a different file that hasn't been read
        test_file2 = os.path.join(test_dir, "test2.txt")
        
        # Create the file first
        with open(test_file2, 'w') as f:
            f.write("Unread file content")
        
        edit_tool2 = FileEditTool()  # New instance
        result = edit_tool2.run_impl(
            file_path=test_file2,  # Different file that hasn't been read
            old_string="content",
            new_string="text",
            replace_all=False
        )
        
        if not result.get("success") and result.get("error_type") == "read_required":
            print("✅ Correctly rejected edit without read")
            print(f"   Expected error: {result.get('error')}")
        else:
            print("❌ Should have rejected edit without read")
            return False
        
        print("")
        
        # Test 5: Read again and test replace_all
        print("📖 Test 5: Reading file again...")
        read_tool.run_impl(file_path=test_file)
        
        # Add another line with 'test' to test replace_all
        result = edit_tool.run_impl(
            file_path=test_file,
            old_string="This is a test file.",
            new_string="This is a test file.\nAnother test line.",
            replace_all=False
        )
        
        if result.get("success"):
            print("✅ Added test line")
        else:
            print(f"❌ Failed to add test line: {result.get('error')}")
            return False
        
        # Now test replace_all
        print("📝 Test 6: Testing replace_all functionality...")
        result = edit_tool.run_impl(
            file_path=test_file,
            old_string="test",
            new_string="demo",
            replace_all=True
        )
        
        if result.get("success"):
            print("✅ Replace all successful")
            print(f"   Operation: {result.get('operation')}")
            print(f"   Matches replaced: {result.get('matches_replaced')}")
        else:
            print("❌ Replace all failed")
            print(f"   Error: {result.get('error')}")
            return False
        
        print("")
        
        # Test 7: Final read to verify changes
        print("📖 Test 7: Final verification read...")
        result = read_tool.run_impl(file_path=test_file)
        
        if result.get("success"):
            print("✅ Final read successful")
            print("   Final content:")
            content_lines = result.get('content', '').split('\n')
            for line in content_lines[:6]:  # Show first 6 lines
                print(f"   {line}")
            if len(content_lines) > 6:
                print("   ...")
        else:
            print("❌ Final read failed")
            print(f"   Error: {result.get('error')}")
            return False
        
        print("")
        print("🎉 All tests passed!")
        return True
        
    except Exception as e:
        print(f"💥 Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up
        try:
            shutil.rmtree(test_dir)
            print(f"🧹 Cleaned up test directory: {test_dir}")
        except Exception as e:
            print(f"⚠️  Failed to clean up test directory: {e}")


if __name__ == "__main__":
    success = test_file_edit_tool()
    sys.exit(0 if success else 1) 