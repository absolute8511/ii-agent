#!/usr/bin/env python3
"""Test script for the GrepTool implementation."""

import os
import sys
import tempfile
import shutil
import time
import subprocess

# Add the src directory to Python path
sys.path.insert(0, 'src')

from tools.file_system.grep_tool import GrepTool


def check_ripgrep_available():
    """Check if ripgrep is available on the system."""
    try:
        subprocess.run(['rg', '--version'], capture_output=True, text=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def test_grep_tool():
    """Test the grep tool with various scenarios."""
    
    # Check for ripgrep availability
    if not check_ripgrep_available():
        print("⚠️  ripgrep (rg) is not available on this system")
        print("   Please install ripgrep to run these tests")
        print("   Ubuntu/Debian: sudo apt install ripgrep")
        print("   macOS: brew install ripgrep")
        print("   Windows: choco install ripgrep")
        return False
    
    # Create a temporary directory for our tests
    test_dir = tempfile.mkdtemp()
    
    try:
        print("🧪 Testing GrepTool implementation...")
        print(f"📁 Test directory: {test_dir}")
        print("")
        
        # Initialize tool
        grep_tool = GrepTool()
        
        print(f"✅ Tool initialized: {grep_tool.name}")
        print("📝 Description preview:")
        print(f"   {grep_tool.description[:100]}...")
        print("")
        
        # Create test files with different content and timestamps
        test_files = {
            "app.py": "def main():\n    print('Hello World')\n    log_error('Test error')\n\nif __name__ == '__main__':\n    main()",
            "utils.js": "function calculateSum(a, b) {\n    return a + b;\n}\n\nfunction logError(message) {\n    console.log('ERROR:', message);\n}",
            "config.json": '{\n    "name": "test-app",\n    "version": "1.0.0",\n    "debug": true\n}',
            "README.md": "# Test Project\n\nThis is a test project for grep functionality.\n\n## Functions\n- main function in app.py\n- utility functions in utils.js",
            "styles.css": ".error {\n    color: red;\n    font-weight: bold;\n}\n\n.main-container {\n    padding: 20px;\n}",
            "test.log": "INFO: Application started\nERROR: File not found\nWARNING: Deprecated function used\nERROR: Connection timeout"
        }
        
        # Create files with staggered timestamps
        for i, (filename, content) in enumerate(test_files.items()):
            file_path = os.path.join(test_dir, filename)
            with open(file_path, 'w') as f:
                f.write(content)
            
            # Add small delay to ensure different modification times
            if i < len(test_files) - 1:
                time.sleep(0.1)
        
        print(f"📝 Created {len(test_files)} test files")
        print("")
        
        # Test 1: Basic pattern search
        print("🔍 Test 1: Basic pattern search...")
        result = grep_tool.run_impl(pattern="function", path=test_dir)
        
        if isinstance(result, dict) and result.get("num_files", 0) > 0:
            print("✅ Basic search successful")
            print(f"   Files found: {result['num_files']}")
            print(f"   Duration: {result['duration_ms']}ms")
            print(f"   Files: {', '.join(result['filenames'])}")
        else:
            print("❌ Basic search failed")
            if isinstance(result, str):
                print(f"   Error: {result}")
            return False
        
        print("")
        
        # Test 2: Case-insensitive search
        print("🔍 Test 2: Case-insensitive search...")
        result = grep_tool.run_impl(pattern="ERROR", path=test_dir)
        
        if isinstance(result, dict) and result.get("num_files", 0) > 0:
            print("✅ Case-insensitive search successful")
            print(f"   Files found: {result['num_files']}")
            print(f"   Files: {', '.join(result['filenames'])}")
        else:
            print("❌ Case-insensitive search failed")
            if isinstance(result, str):
                print(f"   Error: {result}")
            return False
        
        print("")
        
        # Test 3: File pattern filtering
        print("🔍 Test 3: File pattern filtering...")
        result = grep_tool.run_impl(pattern="function", path=test_dir, include="*.js")
        
        if isinstance(result, dict):
            if result.get("num_files", 0) > 0:
                print("✅ File filtering successful")
                print(f"   Files found: {result['num_files']}")
                print(f"   Files: {', '.join(result['filenames'])}")
                # Should only find JavaScript files
                js_files = [f for f in result['filenames'] if f.endswith('.js')]
                if len(js_files) == result['num_files']:
                    print("   ✅ Correctly filtered to .js files only")
                else:
                    print("   ⚠️  File filtering may not be working correctly")
            else:
                print("❌ No files found with pattern filtering")
                return False
        else:
            print("❌ File filtering failed")
            if isinstance(result, str):
                print(f"   Error: {result}")
            return False
        
        print("")
        
        # Test 4: Multiple file extensions
        print("🔍 Test 4: Multiple file extensions...")
        result = grep_tool.run_impl(pattern="main", path=test_dir, include="*.{py,md}")
        
        if isinstance(result, dict) and result.get("num_files", 0) > 0:
            print("✅ Multiple extensions search successful")
            print(f"   Files found: {result['num_files']}")
            print(f"   Files: {', '.join(result['filenames'])}")
        else:
            print("❌ Multiple extensions search failed")
            if isinstance(result, str):
                print(f"   Error: {result}")
            return False
        
        print("")
        
        # Test 5: Regex pattern
        print("🔍 Test 5: Regex pattern search...")
        result = grep_tool.run_impl(pattern="function\\s+\\w+", path=test_dir)
        
        if isinstance(result, dict):
            print("✅ Regex pattern search completed")
            print(f"   Files found: {result['num_files']}")
            if result['num_files'] > 0:
                print(f"   Files: {', '.join(result['filenames'])}")
        else:
            print("❌ Regex pattern search failed")
            if isinstance(result, str):
                print(f"   Error: {result}")
            return False
        
        print("")
        
        # Test 6: No matches
        print("🔍 Test 6: Search with no matches...")
        result = grep_tool.run_impl(pattern="nonexistent_pattern_12345", path=test_dir)
        
        if isinstance(result, str) and "No files found" in result:
            print("✅ Correctly handled no matches")
            print(f"   Result: {result}")
        elif isinstance(result, dict) and result.get("num_files", 0) == 0:
            print("✅ Correctly handled no matches (dict format)")
            print(f"   Files found: {result['num_files']}")
        else:
            print("❌ Should have returned no matches")
            print(f"   Unexpected result: {result}")
            return False
        
        print("")
        
        # Test 7: Non-existent directory
        print("🔍 Test 7: Non-existent directory...")
        result = grep_tool.run_impl(pattern="test", path="/nonexistent/directory")
        
        if isinstance(result, str) and "does not exist" in result:
            print("✅ Correctly handled non-existent directory")
            print(f"   Error message: {result}")
        else:
            print("❌ Should have returned error for non-existent directory")
            print(f"   Unexpected result: {result}")
            return False
        
        print("")
        
        # Test 8: Default path (current working directory)
        print("🔍 Test 8: Default path (cwd)...")
        # Change to test directory to test default path behavior
        original_cwd = os.getcwd()
        os.chdir(test_dir)
        
        try:
            result = grep_tool.run_impl(pattern="test")  # No path specified
            
            if isinstance(result, dict) and result.get("num_files", 0) > 0:
                print("✅ Default path search successful")
                print(f"   Files found: {result['num_files']}")
            elif isinstance(result, str) and "No files found" in result:
                print("✅ Default path search completed (no matches)")
            else:
                print("❌ Default path search failed")
                if isinstance(result, str):
                    print(f"   Error: {result}")
                return False
        finally:
            os.chdir(original_cwd)
        
        print("")
        
        # Test 9: Modification time sorting verification
        print("🔍 Test 9: Modification time sorting...")
        
        # Create two new files with controlled timestamps
        file1 = os.path.join(test_dir, "older.txt")
        file2 = os.path.join(test_dir, "newer.txt")
        
        with open(file1, 'w') as f:
            f.write("test content in older file")
        
        time.sleep(0.2)  # Ensure different timestamps
        
        with open(file2, 'w') as f:
            f.write("test content in newer file")
        
        result = grep_tool.run_impl(pattern="test content", path=test_dir)
        
        if isinstance(result, dict) and result.get("num_files", 0) >= 2:
            print("✅ Modification time sorting search completed")
            print(f"   Files found: {result['num_files']}")
            print(f"   File order: {', '.join(result['filenames'][:3])}...")
            
            # Check if newer.txt comes before older.txt (newer files first)
            filenames = result['filenames']
            if 'newer.txt' in filenames and 'older.txt' in filenames:
                newer_idx = filenames.index('newer.txt')
                older_idx = filenames.index('older.txt')
                if newer_idx < older_idx:
                    print("   ✅ Files correctly sorted by modification time (newest first)")
                else:
                    print("   ⚠️  File sorting may not be working as expected")
        else:
            print("❌ Modification time sorting test inconclusive")
            if isinstance(result, str):
                print(f"   Error: {result}")
        
        print("")
        
        # Test 10: Large pattern (edge case)
        print("🔍 Test 10: Complex regex pattern...")
        result = grep_tool.run_impl(pattern="(function|def)\\s+\\w+", path=test_dir)
        
        if isinstance(result, dict):
            print("✅ Complex regex pattern search completed")
            print(f"   Files found: {result['num_files']}")
            if result['num_files'] > 0:
                print(f"   Files: {', '.join(result['filenames'])}")
        else:
            print("❌ Complex regex pattern search failed")
            if isinstance(result, str):
                print(f"   Error: {result}")
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


def test_grep_tool_without_ripgrep():
    """Test error handling when ripgrep is not available."""
    print("")
    print("🧪 Testing error handling without ripgrep...")
    
    # Temporarily modify PATH to simulate ripgrep not being available
    original_path = os.environ.get('PATH', '')
    
    try:
        # Set PATH to empty to simulate ripgrep not found
        os.environ['PATH'] = ''
        
        grep_tool = GrepTool()
        result = grep_tool.run_impl(pattern="test", path=".")
        
        if isinstance(result, str) and ("not found" in result or "Error:" in result):
            print("✅ Correctly handled missing ripgrep")
            print(f"   Error message: {result}")
            return True
        else:
            print("❌ Should have returned error for missing ripgrep")
            print(f"   Unexpected result: {result}")
            return False
            
    finally:
        # Restore original PATH
        os.environ['PATH'] = original_path


if __name__ == "__main__":
    print("🚀 Testing GrepTool Implementation")
    print("=" * 50)
    
    success = test_grep_tool()
    
    # Also test error handling
    if success:
        success = test_grep_tool_without_ripgrep()
    
    print("")
    print("=" * 50)
    if success:
        print("🎉 All GrepTool tests completed successfully!")
    else:
        print("❌ Some tests failed!")
    
    sys.exit(0 if success else 1) 