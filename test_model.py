#!/usr/bin/env python3
"""
Quick test of the updated NVIDIA NIM model integration.
Run: python test_model.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

async def main():
    print("Testing NVIDIA NIM model integration...")
    print("=" * 60)

    try:
        from backend.services.nvidia_llm import generate_search_terms
        from backend.config import get_settings

        settings = get_settings()
        if not settings.nvidia_keys:
            print("❌ No NVIDIA keys configured. Set NVIDIA_KEY_1/2/3 in .env")
            return False

        print(f"✓ Found {len(settings.nvidia_keys)} NVIDIA keys")
        print(f"✓ Model: {settings.nvidia_model}")
        print("✓ Thinking parameters: REMOVED (compatible with new model)")
        print()

        # Test search term generation
        print("Testing: generate_search_terms('transformer attention mechanisms')")
        result = await generate_search_terms("transformer attention mechanisms")

        print("✓ Response received:")
        print(f"  - Domain: {result.get('domain')}")
        print(f"  - General terms: {result.get('terms_general', [])[:2]}...")
        print(f"  - ArXiv terms: {result.get('terms_arxiv', [])[:2]}...")
        print(f"  - PubMed terms: {result.get('terms_pubmed', [])[:2]}...")
        print()
        print("✅ Model test PASSED")
        return True

    except Exception as e:
        print(f"❌ Model test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
