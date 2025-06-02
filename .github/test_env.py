#!/usr/bin/env python3
"""
Test script to verify environment variables are set
Run this in GitHub Actions to debug secret issues
"""

import os

print("🔍 Testing Environment Variables")
print("=" * 50)

# Check if running in GitHub Actions
if os.environ.get('GITHUB_ACTIONS'):
    print("✅ Running in GitHub Actions")
else:
    print("📍 Running locally")

print("\nChecking secrets:")
print("-" * 50)

secrets = {
    'OPENAI_API_KEY': 'OpenAI API Key',
    'PRINTFUL_API_KEY': 'Printful API Key',
    'PRINTFUL_STORE_ID': 'Printful Store ID',
    'SHOPIFY_STORE': 'Shopify Store Name',
    'SHOPIFY_ACCESS_TOKEN': 'Shopify Access Token',
    'MARKUP_PERCENT': 'Markup Percentage'
}

found = 0
missing = 0

for key, description in secrets.items():
    value = os.environ.get(key)
    if value:
        if key == 'MARKUP_PERCENT':
            print(f"✅ {key}: {value}")
        else:
            # Show length only for security
            print(f"✅ {key}: Found ({len(value)} characters)")
        found += 1
    else:
        print(f"❌ {key}: NOT FOUND")
        missing += 1

print("-" * 50)
print(f"\nSummary: {found} found, {missing} missing")

if missing > 0:
    print("\n⚠️  Missing secrets! Make sure your workflow includes:")
    print("env:")
    print("  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}")
    print("  PRINTFUL_API_KEY: ${{ secrets.PRINTFUL_API_KEY }}")
    print("  # ... etc")
    exit(1)
else:
    print("\n✅ All secrets are properly configured!")
