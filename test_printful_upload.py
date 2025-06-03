#!/usr/bin/env python3
"""
Test script for Printful URL-based file upload
Based on research showing Printful prefers URL references
"""

import os
import requests
import json
import time

# Configuration
PRINTFUL_API_KEY = os.environ.get('PRINTFUL_API_KEY')
STORE_ID = os.environ.get('PRINTFUL_STORE_ID')

# Test image URLs (using free, publicly available images)
TEST_IMAGES = [
    {
        'url': 'https://via.placeholder.com/1800x2400/FF0000/FFFFFF?text=Test+Design',
        'name': 'placeholder_test.png'
    },
    {
        'url': 'https://picsum.photos/1800/2400',
        'name': 'random_test.jpg'
    }
]

def test_url_upload():
    """Test URL-based file upload to Printful."""
    print("\n🧪 Testing URL-based upload method")
    print("=" * 60)
    
    url = 'https://api.printful.com/files'
    headers = {
        'Authorization': f'Bearer {PRINTFUL_API_KEY}',
        'Content-Type': 'application/json',
        'X-PF-Store-Id': str(STORE_ID)
    }
    
    for test_image in TEST_IMAGES:
        print(f"\n📸 Testing with: {test_image['name']}")
        print(f"   URL: {test_image['url']}")
        
        # Prepare the request data
        data = {
            'url': test_image['url'],
            'type': 'default',
            'filename': test_image['name'],
            'visible': True,
            'options': []
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            print(f"   Status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                result = response.json()
                if 'result' in result:
                    file_id = result['result']['id']
                    file_url = result['result'].get('url', 'N/A')
                    print(f"   ✅ Success! File ID: {file_id}")
                    print(f"   📎 File URL: {file_url}")
                    
                    # Test creating a product with this file
                    test_create_product(file_id, headers)
                else:
                    print(f"   ❌ Unexpected response: {json.dumps(result, indent=2)}")
            else:
                print(f"   ❌ Failed: {response.text[:200]}...")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Delay between tests
        time.sleep(2)

def test_create_product(file_id, headers):
    """Test creating a product with the uploaded file."""
    print(f"\n   🛍️ Testing product creation with file ID: {file_id}")
    
    url = 'https://api.printful.com/store/products'
    
    product_data = {
        'sync_product': {
            'name': f'Test Product {int(time.time())}'
        },
        'sync_variants': [{
            'variant_id': 4011,  # Unisex Staple T-Shirt - S - Black
            'retail_price': '25.00',
            'is_enabled': True,
            'files': [{  # Must be an array
                'id': file_id,
                'placement': 'front'
            }]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=product_data)
        print(f"   Product creation status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            if 'result' in result:
                product_id = result['result']['sync_product']['id']
                print(f"   ✅ Product created! ID: {product_id}")
            else:
                print(f"   ❓ Response: {json.dumps(result, indent=2)}")
        else:
            print(f"   ❌ Failed: {response.text[:200]}...")
            
            # Check for store type issue
            if "Manual Order / API platform" in response.text:
                print("   ⚠️  Note: Product creation only works with Manual/API stores")
                print("   💡 For Shopify stores, products are created during sync")
                
    except Exception as e:
        print(f"   ❌ Error creating product: {e}")

def test_list_files():
    """List existing files in the Printful library."""
    print("\n📂 Listing existing files")
    print("=" * 60)
    
    url = 'https://api.printful.com/files'
    headers = {
        'Authorization': f'Bearer {PRINTFUL_API_KEY}',
        'X-PF-Store-Id': str(STORE_ID)
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                files = result['result']
                print(f"Found {len(files)} files in library")
                
                # Show first 3 files
                for i, file in enumerate(files[:3]):
                    print(f"\nFile {i+1}:")
                    print(f"  ID: {file.get('id')}")
                    print(f"  Name: {file.get('filename')}")
                    print(f"  URL: {file.get('url')}")
                    print(f"  Type: {file.get('type')}")
            else:
                print(f"Response: {json.dumps(result, indent=2)}")
        else:
            print(f"Failed: {response.text[:200]}...")
            
    except Exception as e:
        print(f"Error: {e}")

def main():
    """Run all tests."""
    print("=" * 60)
    print("PRINTFUL URL-BASED UPLOAD TESTS")
    print("=" * 60)
    print(f"Store ID: {STORE_ID}")
    print(f"API Key: {'*' * 10}...{PRINTFUL_API_KEY[-4:] if PRINTFUL_API_KEY else 'NOT SET'}")
    
    if not PRINTFUL_API_KEY or not STORE_ID:
        print("\n❌ Missing environment variables!")
        return
    
    # Run tests
    test_list_files()
    test_url_upload()
    
    print("\n" + "=" * 60)
    print("Tests complete!")
    print("\n💡 Key findings:")
    print("- Printful uses URL-based file uploads, not multipart")
    print("- Files must be hosted on accessible URLs")
    print("- The 'files' parameter must always be an array")
    print("- Product creation may be limited for Shopify stores")

if __name__ == "__main__":
    main()
