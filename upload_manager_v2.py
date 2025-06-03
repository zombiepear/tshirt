#!/usr/bin/env python3
"""
Upload Manager v2 - Compatible with Printful API 2025
Key changes:
- Uses URL-based uploads (no direct file uploads)
- OAuth Bearer token authentication
- Uses "front_large" placement (not "front")
- Proper rate limiting (120 req/min)
- Handles Cloudflare protection
"""

import os
import json
import time
import requests
import argparse
from datetime import datetime
from pathlib import Path
import hashlib
import base64
from urllib.parse import urlparse

# Configuration
PRINTFUL_API_KEY = os.environ.get("PRINTFUL_API_KEY")  # OAuth Bearer token
PRINTFUL_STORE_ID = os.environ.get("PRINTFUL_STORE_ID")
SHOPIFY_STORE = os.environ.get("SHOPIFY_STORE")
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN")
MARKUP_PERCENT = float(os.environ.get("MARKUP_PERCENT", "1.4"))

# GitHub repository info for hosting files
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")  # format: owner/repo
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")  # for creating releases

# API endpoints
PRINTFUL_API_BASE = "https://api.printful.com"
SHOPIFY_API_BASE = f"https://{SHOPIFY_STORE}.myshopify.com/admin/api/2024-01" if SHOPIFY_STORE else None

# Upload tracking file
UPLOAD_TRACKER_FILE = "upload_tracker.json"

class UploadManagerV2:
    def __init__(self, upload_dir=".", dry_run=False):
        self.upload_dir = Path(upload_dir)
        self.dry_run = dry_run
        self.tracker = self.load_tracker()
        self.session = self.create_session()
        self.rate_limiter = RateLimiter()
        
    def create_session(self):
        """Create session with proper headers for Printful API 2025"""
        session = requests.Session()
        
        # Required headers for Printful API
        headers = {
            'User-Agent': 'T-Shirt-Generator/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # OAuth Bearer token authentication
        if PRINTFUL_API_KEY:
            headers['Authorization'] = f'Bearer {PRINTFUL_API_KEY.strip()}'
        
        # Store ID header if using account-level token
        if PRINTFUL_STORE_ID:
            headers['X-PF-Store-Id'] = PRINTFUL_STORE_ID.strip()
            
        session.headers.update(headers)
        return session
        
    def load_tracker(self):
        """Load upload tracking data"""
        if os.path.exists(UPLOAD_TRACKER_FILE):
            with open(UPLOAD_TRACKER_FILE, 'r') as f:
                return json.load(f)
        return {"uploaded": {}, "failed": {}, "stats": {"total_uploaded": 0, "total_failed": 0}}
    
    def save_tracker(self):
        """Save upload tracking data"""
        with open(UPLOAD_TRACKER_FILE, 'w') as f:
            json.dump(self.tracker, f, indent=2)
    
    def get_file_hash(self, filepath):
        """Generate hash of file for tracking"""
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def is_uploaded(self, filepath):
        """Check if file has been successfully uploaded"""
        file_hash = self.get_file_hash(filepath)
        return file_hash in self.tracker["uploaded"]
    
    def upload_to_github_release(self, filepath):
        """Upload file to GitHub release and return public URL"""
        if not GITHUB_REPO or not GITHUB_TOKEN:
            # Fallback: use raw GitHub URL if file is in repo
            return f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{filepath.name}"
        
        # This would create a GitHub release and upload the file
        # For now, returning a placeholder URL
        # In production, implement GitHub release API upload
        return f"https://github.com/{GITHUB_REPO}/releases/download/designs/{filepath.name}"
    
    def get_public_url(self, filepath):
        """Get or create a public URL for the design file"""
        # Option 1: If running in GitHub Actions, use artifact URL
        if os.environ.get("GITHUB_ACTIONS"):
            # Files are available via GitHub's CDN during workflow
            return f"https://raw.githubusercontent.com/{os.environ.get('GITHUB_REPOSITORY')}/main/{filepath.name}"
        
        # Option 2: Upload to a public hosting service
        # For this example, we'll assume files are hosted elsewhere
        # In production, you'd upload to S3, Cloudinary, etc.
        
        # Placeholder - you need to implement actual file hosting
        print(f"  ⚠️  Warning: File hosting not configured. Using placeholder URL.")
        return f"https://example.com/designs/{filepath.name}"
    
    def create_printful_product(self, filepath, design_info):
        """Create product in Printful using URL reference"""
        if not PRINTFUL_API_KEY:
            print("  ❌ Printful API key not configured")
            return None
        
        # Get public URL for the design
        design_url = self.get_public_url(filepath)
        print(f"  📎 Design URL: {design_url}")
        
        try:
            # Rate limiting
            self.rate_limiter.wait_if_needed()
            
            print("  📤 Creating Printful product...")
            
            # Product data following Printful API 2025 format
            product_data = {
                "sync_product": {
                    "name": f"{design_info['category'].title()} - {design_info['theme'].title()}"
                },
                "sync_variants": [
                    {
                        "variant_id": 4012,  # Bella + Canvas 3001 - S
                        "retail_price": f"{design_info['retail_price']:.2f}",
                        "files": [
                            {
                                "type": "front_large",  # CRITICAL: Use "front_large" not "front"!
                                "url": design_url
                            }
                        ]
                    },
                    {
                        "variant_id": 4013,  # M
                        "retail_price": f"{design_info['retail_price']:.2f}",
                        "files": [
                            {
                                "type": "front_large",
                                "url": design_url
                            }
                        ]
                    },
                    {
                        "variant_id": 4014,  # L
                        "retail_price": f"{design_info['retail_price']:.2f}",
                        "files": [
                            {
                                "type": "front_large",
                                "url": design_url
                            }
                        ]
                    },
                    {
                        "variant_id": 4015,  # XL
                        "retail_price": f"{design_info['retail_price']:.2f}",
                        "files": [
                            {
                                "type": "front_large",
                                "url": design_url
                            }
                        ]
                    },
                    {
                        "variant_id": 4016,  # 2XL
                        "retail_price": f"{design_info['retail_price'] * 1.12:.2f}",
                        "files": [
                            {
                                "type": "front_large",
                                "url": design_url
                            }
                        ]
                    }
                ]
            }
            
            # Create product endpoint
            url = f"{PRINTFUL_API_BASE}/store/products"
            
            response = self.session.post(
                url,
                json=product_data,
                timeout=30
            )
            
            # Log response for debugging
            print(f"  Response status: {response.status_code}")
            
            if response.status_code == 429:
                # Rate limited
                retry_after = int(response.headers.get('Retry-After', 60))
                print(f"  ⏳ Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self.create_printful_product(filepath, design_info)  # Retry
            
            if response.status_code != 200:
                print(f"  ❌ Printful error: {response.status_code} - {response.text[:200]}")
                return None
            
            result = response.json()
            product_id = result.get("result", {}).get("id")
            
            if product_id:
                print(f"  ✅ Printful product created: ID {product_id}")
                return {
                    "printful_product_id": product_id,
                    "design_url": design_url
                }
            else:
                print(f"  ❌ Unexpected response format: {result}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"  ⚠️  Request timed out")
            return None
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            return None
    
    def create_shopify_product(self, filepath, design_info, printful_data=None):
        """Create product in Shopify"""
        if not SHOPIFY_STORE or not SHOPIFY_ACCESS_TOKEN:
            print("  ❌ Shopify not configured")
            return None
            
        headers = {
            "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN.strip(),
            "Content-Type": "application/json"
        }
        
        try:
            print("  🛍️  Creating Shopify product...")
            
            # Read and encode image for Shopify
            with open(filepath, 'rb') as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            product_data = {
                "product": {
                    "title": f"{design_info['category'].title()} T-Shirt - {design_info['theme'].title()}",
                    "body_html": f"<p>AI-generated {design_info['category']} themed t-shirt featuring {design_info['theme']}.</p>",
                    "vendor": "AI Designs",
                    "product_type": "T-Shirt",
                    "tags": f"{design_info['category']}, ai-generated, t-shirt",
                    "images": [
                        {
                            "attachment": image_base64,
                            "filename": os.path.basename(filepath)
                        }
                    ],
                    "variants": [
                        {
                            "option1": "S",
                            "price": f"{design_info['retail_price']:.2f}",
                            "sku": f"TEE-{design_info['file_hash'][:8]}-S"
                        },
                        {
                            "option1": "M",
                            "price": f"{design_info['retail_price']:.2f}",
                            "sku": f"TEE-{design_info['file_hash'][:8]}-M"
                        },
                        {
                            "option1": "L",
                            "price": f"{design_info['retail_price']:.2f}",
                            "sku": f"TEE-{design_info['file_hash'][:8]}-L"
                        },
                        {
                            "option1": "XL",
                            "price": f"{design_info['retail_price']:.2f}",
                            "sku": f"TEE-{design_info['file_hash'][:8]}-XL"
                        },
                        {
                            "option1": "2XL",
                            "price": f"{design_info['retail_price'] * 1.12:.2f}",
                            "sku": f"TEE-{design_info['file_hash'][:8]}-2XL"
                        }
                    ],
                    "options": [
                        {
                            "name": "Size",
                            "values": ["S", "M", "L", "XL", "2XL"]
                        }
                    ]
                }
            }
            
            # Add Printful product ID as metafield if available
            if printful_data and printful_data.get('printful_product_id'):
                product_data["product"]["metafields"] = [
                    {
                        "namespace": "printful",
                        "key": "product_id",
                        "value": str(printful_data['printful_product_id']),
                        "type": "single_line_text_field"
                    }
                ]
            
            url = f"{SHOPIFY_API_BASE}/products.json"
            response = requests.post(url, json=product_data, headers=headers, timeout=30)
            
            if response.status_code != 201:
                print(f"  ❌ Shopify error: {response.status_code} - {response.text[:200]}")
                return None
                
            product = response.json()["product"]
            print(f"  ✅ Shopify product created: {product['title']}")
            
            return {
                "shopify_product_id": product["id"],
                "shopify_handle": product["handle"]
            }
            
        except Exception as e:
            print(f"  ❌ Shopify error: {str(e)}")
            return None
    
    def extract_design_info(self, filename):
        """Extract category and theme from filename"""
        parts = filename.replace('.png', '').split('_')
        
        if len(parts) >= 3:
            if parts[0] == 'design':
                category = parts[1]
                theme_parts = parts[2:-2] if len(parts) > 4 else parts[2:-1]
                theme = ' '.join(theme_parts).replace('_', ' ')
                return category, theme
        
        return "custom", filename.replace('design_', '').replace('.png', '')
    
    def process_file(self, filepath):
        """Process a single design file"""
        filename = os.path.basename(filepath)
        file_hash = self.get_file_hash(filepath)
        
        print(f"\n{'='*60}")
        print(f"📁 Processing: {filename}")
        
        # Check if already uploaded
        if self.is_uploaded(filepath):
            upload_info = self.tracker["uploaded"][file_hash]
            print(f"✅ Already uploaded on {upload_info['upload_date']}")
            return False
        
        # Extract design information
        category, theme = self.extract_design_info(filename)
        
        # Calculate pricing
        base_price = 15.00  # Printful's base price for Bella + Canvas 3001
        retail_price = base_price * MARKUP_PERCENT
        
        design_info = {
            "filename": filename,
            "filepath": str(filepath),
            "file_hash": file_hash,
            "category": category,
            "theme": theme,
            "base_price": base_price,
            "retail_price": retail_price
        }
        
        print(f"📋 Category: {category}")
        print(f"🎨 Theme: {theme}")
        print(f"💰 Retail Price: ${retail_price:.2f} (markup: {MARKUP_PERCENT}x)")
        
        if self.dry_run:
            print("🔍 DRY RUN - Would upload this file")
            return True
        
        # Create Printful product
        printful_result = None
        if PRINTFUL_API_KEY:
            printful_result = self.create_printful_product(filepath, design_info)
        
        # Create Shopify product
        shopify_result = None
        if SHOPIFY_STORE:
            shopify_result = self.create_shopify_product(filepath, design_info, printful_result)
        
        # Track upload
        if printful_result or shopify_result:
            self.tracker["uploaded"][file_hash] = {
                "filename": filename,
                "upload_date": datetime.now().isoformat(),
                "category": category,
                "theme": theme,
                "base_price": base_price,
                "retail_price": retail_price,
                **(printful_result or {}),
                **(shopify_result or {})
            }
            self.tracker["stats"]["total_uploaded"] += 1
            self.save_tracker()
            print("✅ Upload successful!")
            return True
        else:
            self.tracker["failed"][file_hash] = {
                "filename": filename,
                "fail_date": datetime.now().isoformat(),
                "category": category,
                "theme": theme,
                "error": "Failed to create product"
            }
            self.tracker["stats"]["total_failed"] += 1
            self.save_tracker()
            print("❌ Upload failed!")
            return False
    
    def process_directory(self):
        """Process all PNG files in the upload directory"""
        png_files = list(self.upload_dir.glob("design_*.png"))
        
        if not png_files:
            print(f"No design files found in {self.upload_dir}")
            return
        
        print(f"Found {len(png_files)} design files")
        
        uploaded = 0
        skipped = 0
        failed = 0
        
        for filepath in png_files:
            try:
                if self.is_uploaded(filepath):
                    skipped += 1
                elif self.process_file(filepath):
                    uploaded += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"Error processing {filepath}: {str(e)}")
                failed += 1
        
        # Summary
        print(f"\n{'='*60}")
        print("📊 UPLOAD SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Uploaded: {uploaded}")
        print(f"⏭️  Skipped: {skipped}")
        print(f"❌ Failed: {failed}")
        print(f"📁 Total: {len(png_files)}")
        print(f"\n💾 Total all-time uploads: {self.tracker['stats']['total_uploaded']}")

class RateLimiter:
    """Handle Printful API rate limiting (120 requests/minute)"""
    def __init__(self):
        self.requests = []
        self.max_requests = 120
        self.window = 60  # seconds
        
    def wait_if_needed(self):
        """Wait if necessary to respect rate limits"""
        now = time.time()
        
        # Remove old requests outside the window
        self.requests = [req_time for req_time in self.requests if now - req_time < self.window]
        
        # If at limit, wait
        if len(self.requests) >= self.max_requests:
            sleep_time = self.window - (now - self.requests[0]) + 1
            print(f"  ⏳ Rate limit reached. Waiting {sleep_time:.1f} seconds...")
            time.sleep(sleep_time)
            
        # Add current request
        self.requests.append(now)
        
        # Also add a small delay between requests
        time.sleep(0.5)

def main():
    parser = argparse.ArgumentParser(
        description='Upload t-shirt designs to Printful and Shopify (2025 API)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
IMPORTANT: Printful API 2025 Requirements
- Uses OAuth Bearer tokens (not old API keys)
- Files must be hosted at public URLs
- Uses "front_large" placement (not "front")
- Rate limit: 120 requests/minute

Examples:
  python upload_manager_v2.py                    # Process current directory
  python upload_manager_v2.py --dir ./designs    # Process specific directory
  python upload_manager_v2.py --dry-run          # Test without uploading
  python upload_manager_v2.py --shopify-only     # Skip Printful
        """
    )
    
    parser.add_argument('--dir', type=str, default='.', help='Directory containing design files')
    parser.add_argument('--file', type=str, help='Upload a specific file')
    parser.add_argument('--dry-run', action='store_true', help='Test without uploading')
    parser.add_argument('--retry-failed', action='store_true', help='Retry previously failed uploads')
    parser.add_argument('--reset-tracker', action='store_true', help='Reset upload tracker')
    parser.add_argument('--shopify-only', action='store_true', help='Skip Printful, only upload to Shopify')
    parser.add_argument('--check-auth', action='store_true', help='Test API authentication')
    
    args = parser.parse_args()
    
    # Check authentication
    if args.check_auth:
        manager = UploadManagerV2()
        print("🔐 Checking API authentication...")
        
        # Test Printful
        if PRINTFUL_API_KEY:
            response = manager.session.get(f"{PRINTFUL_API_BASE}/oauth/scopes")
            if response.status_code == 200:
                print("✅ Printful authentication successful")
                print(f"   Scopes: {response.json()}")
            else:
                print(f"❌ Printful authentication failed: {response.status_code}")
        
        # Test Shopify
        if SHOPIFY_ACCESS_TOKEN:
            headers = {"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN}
            response = requests.get(f"{SHOPIFY_API_BASE}/shop.json", headers=headers)
            if response.status_code == 200:
                print("✅ Shopify authentication successful")
            else:
                print(f"❌ Shopify authentication failed: {response.status_code}")
        
        return
    
    # Skip Printful if requested
    if args.shopify_only:
        os.environ['PRINTFUL_API_KEY'] = ''
        print("📝 Shopify-only mode enabled")
    
    # Reset tracker if requested
    if args.reset_tracker:
        if input("Are you sure you want to reset the tracker? (yes/no): ").lower() == 'yes':
            if os.path.exists(UPLOAD_TRACKER_FILE):
                os.remove(UPLOAD_TRACKER_FILE)
                print("Tracker reset!")
        return
    
    # Create upload manager
    manager = UploadManagerV2(upload_dir=args.dir, dry_run=args.dry_run)
    
    # Process files
    if args.file:
        filepath = Path(args.file)
        if filepath.exists():
            manager.process_file(filepath)
        else:
            print(f"File not found: {args.file}")
    else:
        if args.retry_failed:
            print("Retrying failed uploads...")
            for file_hash, info in list(manager.tracker["failed"].items()):
                filepath = Path(info["filename"])
                if filepath.exists():
                    del manager.tracker["failed"][file_hash]
                    manager.save_tracker()
                    manager.process_file(filepath)
        else:
            manager.process_directory()

if __name__ == "__main__":
    main()
