#!/usr/bin/env python3
"""
Test script to debug Printful file upload
This will help identify the correct format for file uploads
"""

import os
import requests
import base64
from io import BytesIO
from PIL import Image
import json

# Configuration
PRINTFUL_API_KEY = os.environ.get('PRINTFUL_API_KEY')
STORE_ID = os.environ.get('PRINTFUL_STORE_ID')

def create_test_image():
    """Create a simple test image."""
    # Create a simple red square
    img = Image.new('RGB', (100, 100), color='red')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()

def test_multipart_upload_v1():
    """Test multipart upload with 'file' parameter."""
    print("\n🧪 Test 1: Multipart upload with 'file' parameter")
    
    url = f'https://api.printful.com/files'
    headers = {
        'Authorization': f'Bearer {PRINTFUL_API_KEY}'
    }
    
    image_data = create_test_image()
    files = {
        'file': ('test_image.png', BytesIO(image_data), 'image/png')
    }
    
    data = {
        'store_id': STORE_ID
    }
    
    try:
        response = requests.post(url, headers=headers, files=files, data=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {e}")

def test_multipart_upload_v2():
    """Test multipart upload with 'file[]' parameter."""
    print("\n🧪 Test 2: Multipart upload with 'file[]' parameter")
    
    url = f'https://api.printful.com/files'
    headers = {
        'Authorization': f'Bearer {PRINTFUL_API_KEY}'
    }
    
    image_data = create_test_image()
    files = {
        'file[]': ('test_image.png', BytesIO(image_data), 'image/png')
    }
    
    data = {
        'store_id': STORE_ID
    }
    
    try:
        response = requests.post(url, headers=headers, files=files, data=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {e}")

def test_multipart_upload_v3():
    """Test multipart upload with list of tuples (true array)."""
    print("\n🧪 Test 3: Multipart upload with list of tuples")
    
    url = f'https://api.printful.com/files'
    headers = {
        'Authorization': f'Bearer {PRINTFUL_API_KEY}'
    }
    
    image_data = create_test_image()
    files = [
        ('file', ('test_image.png', BytesIO(image_data), 'image/png'))
    ]
    
    data = {
        'store_id': STORE_ID
    }
    
    try:
        response = requests.post(url, headers=headers, files=files, data=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {e}")

def test_base64_upload():
    """Test base64 upload method."""
    print("\n🧪 Test 4: Base64 upload")
    
    url = f'https://api.printful.com/files'
    headers = {
        'Authorization': f'Bearer {PRINTFUL_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    image_data = create_test_image()
    image_b64 = base64.b64encode(image_data).decode('utf-8')
    
    payload = {
        'store_id': int(STORE_ID),
        'type': 'default',
        'files': [
            {
                'type': 'default',
                'url': f'data:image/png;base64,{image_b64}',
                'filename': 'test_image.png'
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {e}")

def test_url_with_store_id():
    """Test with store_id in URL."""
    print("\n🧪 Test 5: Multipart upload with store_id in URL")
    
    url = f'https://api.printful.com/files?store_id={STORE_ID}'
    headers = {
        'Authorization': f'Bearer {PRINTFUL_API_KEY}'
    }
    
    image_data = create_test_image()
    files = [
        ('file', ('test_image.png', BytesIO(image_data), 'image/png'))
    ]
    
    try:
        response = requests.post(url, headers=headers, files=files)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {e}")

def main():
    """Run all tests."""
    print("=" * 60)
    print("PRINTFUL FILE UPLOAD TESTS")
    print("=" * 60)
    print(f"Store ID: {STORE_ID}")
    print(f"API Key: {'*' * 10}...{PRINTFUL_API_KEY[-4:] if PRINTFUL_API_KEY else 'NOT SET'}")
    
    if not PRINTFUL_API_KEY or not STORE_ID:
        print("\n❌ Missing environment variables!")
        return
    
    # Run all tests
    test_multipart_upload_v1()
    test_multipart_upload_v2()
    test_multipart_upload_v3()
    test_base64_upload()
    test_url_with_store_id()
    
    print("\n" + "=" * 60)
    print("Tests complete!")

if __name__ == "__main__":
    main()
