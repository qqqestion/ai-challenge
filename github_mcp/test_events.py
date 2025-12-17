#!/usr/bin/env python3
"""
Test script for GitHub events API functions.
"""

import asyncio
import json
from tools import get_user_events, get_repo_events


async def main():
    """Test GitHub events functions."""
    print("=" * 60)
    print("Testing GitHub Events API Functions")
    print("=" * 60)

    # Test 1: Get user events
    print("\n📅 Test 1: Get user events")
    print("-" * 60)
    result = await get_user_events("qqqestion", limit=5)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Test 2: Get repo events
    print("\n📅 Test 2: Get repo events")
    print("-" * 60)
    result = await get_repo_events("qqqestion", "ai-challenge", limit=5)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Test 3: Test with non-existent user
    print("\n📅 Test 3: Non-existent user")
    print("-" * 60)
    result = await get_user_events("nonexistentuser12345", limit=5)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print("✅ Tests completed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

