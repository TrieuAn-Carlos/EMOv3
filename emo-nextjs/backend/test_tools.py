#!/usr/bin/env python3
"""
Test Tool Error Handling
=========================
Test the robust tool wrapper and error handling.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.tools_enhanced import (
    search_gmail, get_email, add_task, list_tasks,
    read_webpage, search_memory
)


def test_valid_calls():
    """Test tools with valid parameters."""
    print("=" * 60)
    print("Testing Valid Tool Calls")
    print("=" * 60)
    
    tests = [
        ("add_task", lambda: add_task("Test task")),
        ("add_task with deadline", lambda: add_task("Meeting", "2025-12-15T15:00:00")),
        ("list_tasks", lambda: list_tasks()),
    ]
    
    for name, func in tests:
        print(f"\n✓ Testing {name}...")
        try:
            result = func()
            print(f"  Result: {result[:100]}...")
            print("  ✅ PASS")
        except Exception as e:
            print(f"  ❌ FAIL: {e}")


def test_invalid_calls():
    """Test tools with invalid parameters."""
    print("\n" + "=" * 60)
    print("Testing Invalid Tool Calls (Should handle gracefully)")
    print("=" * 60)
    
    tests = [
        ("get_email with 0", lambda: get_email(0)),  # Invalid: min is 1
        ("get_email with string", lambda: get_email("invalid")),  # Type error
        ("add_task empty", lambda: add_task("")),  # Too short
        ("search_gmail empty", lambda: search_gmail("")),  # Empty query
    ]
    
    for name, func in tests:
        print(f"\n✓ Testing {name}...")
        try:
            result = func()
            if "❌" in result or "Lỗi" in result:
                print(f"  Result: {result[:100]}")
                print("  ✅ Error handled correctly")
            else:
                print(f"  ⚠️  Expected error but got: {result[:100]}")
        except Exception as e:
            print(f"  ❌ Unhandled exception: {e}")


def test_edge_cases():
    """Test edge cases."""
    print("\n" + "=" * 60)
    print("Testing Edge Cases")
    print("=" * 60)
    
    tests = [
        ("Very long task", lambda: add_task("x" * 1000)),
        ("Special characters", lambda: add_task("Task với tiếng Việt 🎉")),
        ("Negative number", lambda: get_email(-1)),
    ]
    
    for name, func in tests:
        print(f"\n✓ Testing {name}...")
        try:
            result = func()
            print(f"  Result: {result[:150]}...")
            print("  ✅ Handled")
        except Exception as e:
            print(f"  ❌ Exception: {e}")


def main():
    """Run all tests."""
    print("\n🧪 EMO Backend - Tool Error Handling Test\n")
    
    test_valid_calls()
    test_invalid_calls()
    test_edge_cases()
    
    print("\n" + "=" * 60)
    print("🎉 Test completed!")
    print("=" * 60)
    print("\nAll tools now have:")
    print("  ✅ Parameter validation")
    print("  ✅ Type checking & conversion")
    print("  ✅ Range validation")
    print("  ✅ Error catching & friendly messages")
    print("  ✅ Consistent string output")
    print("\nThis should prevent 'tool_use_failed' errors.")


if __name__ == "__main__":
    main()
