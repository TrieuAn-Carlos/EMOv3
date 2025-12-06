"""
Test script for 3-Tier Memory System
=====================================
Tests: short-term, long-term, and project memory tools
"""

import sys
sys.path.insert(0, '.')

from tools import (
    save_short_term_memory,
    save_long_term_memory,
    save_project_memory,
    query_short_term,
    query_long_term,
    query_project,
    list_all_projects,
    update_long_term_memory,
)

def test_memory_system():
    print("=" * 64)
    print("       3-TIER MEMORY SYSTEM TEST")
    print("=" * 64)
    
    # Test 1: Short-term memory
    print("\n📝 Test 1: SHORT-TERM MEMORY")
    print("-" * 40)
    
    result = save_short_term_memory.invoke({
        "content": "User is currently tired and prefers brief responses",
        "context": "User mentioned being exhausted from work",
        "importance": "high"
    })
    print(f"Save: {result}")
    
    result = save_short_term_memory.invoke({
        "content": "Working on a presentation for tomorrow",
        "context": "Current task context",
        "importance": "normal"
    })
    print(f"Save: {result}")
    
    result = query_short_term.invoke({"query": "user mood preferences"})
    print(f"\nQuery result:\n{result}")
    
    # Test 2: Long-term memory
    print("\n\n🧠 Test 2: LONG-TERM MEMORY (Permanent)")
    print("-" * 40)
    
    result = save_long_term_memory.invoke({
        "fact": "User's name is Joshua",
        "category": "identity"
    })
    print(f"Save: {result}")
    
    result = save_long_term_memory.invoke({
        "fact": "User is a Computer Science student",
        "category": "identity"
    })
    print(f"Save: {result}")
    
    result = save_long_term_memory.invoke({
        "fact": "User prefers Python over JavaScript",
        "category": "preference"
    })
    print(f"Save: {result}")
    
    result = save_long_term_memory.invoke({
        "fact": "User's birthday is March 15th",
        "category": "date"
    })
    print(f"Save: {result}")
    
    result = query_long_term.invoke({"query": "who is the user"})
    print(f"\nQuery result:\n{result}")
    
    # Test 3: Project memory
    print("\n\n📁 Test 3: PROJECT MEMORY")
    print("-" * 40)
    
    result = save_project_memory.invoke({
        "project_name": "Intro to CS Final Project",
        "content": "Build a simple chatbot using Python",
        "content_type": "goal"
    })
    print(f"Save: {result}")
    
    result = save_project_memory.invoke({
        "project_name": "Intro to CS Final Project",
        "content": "Need to implement NLP for intent recognition",
        "content_type": "requirement"
    })
    print(f"Save: {result}")
    
    result = save_project_memory.invoke({
        "project_name": "Intro to CS Final Project",
        "content": "Completed basic input/output handling",
        "content_type": "progress"
    })
    print(f"Save: {result}")
    
    result = save_project_memory.invoke({
        "project_name": "Personal Website",
        "content": "Create portfolio website with React",
        "content_type": "goal"
    })
    print(f"Save: {result}")
    
    # Query specific project
    result = query_project.invoke({
        "project_name": "Intro to CS Final Project",
        "query": ""
    })
    print(f"\nProject details:\n{result}")
    
    # List all projects
    result = list_all_projects.invoke({})
    print(f"\nAll projects:\n{result}")
    
    # Test 4: Update long-term memory
    print("\n\n🔄 Test 4: UPDATE LONG-TERM MEMORY")
    print("-" * 40)
    
    result = update_long_term_memory.invoke({
        "old_fact": "User prefers Python over JavaScript",
        "new_fact": "User loves both Python and TypeScript",
        "category": "preference"
    })
    print(f"Update: {result}")
    
    result = query_long_term.invoke({"query": "programming preferences"})
    print(f"\nUpdated query:\n{result}")
    
    print("\n" + "=" * 64)
    print("✅ All 3-tier memory tests completed!")
    print("=" * 64)
    
    # Show what was saved to user_config.json
    print("\n📄 Checking user_config.json for long-term facts...")
    import json
    try:
        with open("user_config.json", "r") as f:
            config = json.load(f)
        print(json.dumps(config.get("long_term_facts", {}), indent=2))
    except Exception as e:
        print(f"Could not read config: {e}")


if __name__ == "__main__":
    test_memory_system()
