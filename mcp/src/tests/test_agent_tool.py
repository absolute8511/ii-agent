#!/usr/bin/env python3
"""Test script for the Agent Tool implementation."""

import os
import sys
import asyncio

# Add the src directory to Python path
sys.path.insert(0, 'src')

from tools.agent.agent_tool import AgentTool


def test_agent_tool():
    """Test the agent tool with various prompts."""
    
    # Check for API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("⚠️  Please set ANTHROPIC_API_KEY environment variable to test with real API calls")
        print("   Example: export ANTHROPIC_API_KEY='your-api-key-here'")
        print("")
        print("🧪 Running structure test with placeholder key...")
        os.environ['ANTHROPIC_API_KEY'] = 'test-key-placeholder'
    
    # Initialize the agent tool
    agent = AgentTool()
    print(f"✅ Agent tool initialized: {agent.name}")
    print(f"📝 Description length: {len(agent.description)} characters")
    print("")
    
    # Test cases
    test_cases = [
        {
            "name": "Simple File Search",
            "prompt": "Search for Python files in the current directory and tell me what you find. Focus on the main files and their purposes.",
            "dangerous": False
        },
        {
            "name": "Code Analysis", 
            "prompt": "Look for any configuration files in this codebase and analyze what they contain. I'm particularly interested in dependencies and setup.",
            "dangerous": False
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"🧪 Test {i}: {test_case['name']}")
        print(f"📝 Prompt: {test_case['prompt'][:100]}...")
        print("🔄 Executing...")
        
        try:
            result = agent.run_impl(
                prompt=test_case["prompt"],
                dangerous_skip_permissions=test_case["dangerous"]
            )
            
            print(f"✅ Result:")
            print(f"   {result}")
            print("")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print("")


if __name__ == "__main__":
    print("🚀 Testing Agent Tool Implementation")
    print("=" * 50)
    test_agent_tool() 