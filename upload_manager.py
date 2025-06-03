#!/usr/bin/env python3
"""
Upload Manager - Batch upload t-shirt designs to Printful and Shopify
Processes all designs in a directory and tracks upload status
"""

import os
import json
import time
import requests
import argparse
from datetime import datetime
from pathlib import Path
from PIL import Image
import base64
import hashlib

# Configuration
PRINTFUL_API_KEY = os.environ.get("PRINTFUL_API_KEY")
PRINTFUL_STORE_ID = os.environ.get("PRINTFUL_STORE_ID")
SHOPIFY_STORE = os.environ.get("SHOPIFY_STORE")
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN")
MARKUP_PERCENT = float(os.environ.get("MARKUP_PERCENT", "1.4"))

# API endpoints
PRINTFUL_API_BASE = "https://api.printful.com"
SHOPIFY_API_BASE = f"https://{SHOPIFY_STORE}.myshopify.com/admin/api/2024-01" if SHOPIFY_STORE else None

# Upload tracking file
UPLOAD_TRACKER_FILE = "upload_tracker.json"

class UploadManager:
    def __init__(self, upload_dir=".", dry_run=False):
        self.upload_dir = Path(upload_dir)
        self.dry_run = dry_run
        self.tracker = self.load_tracker()
        
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
    
    def extract_design_info(self, filename):
        """Extract category and theme from filename"""
        # Pattern: design_category_theme_timestamp.png
        parts = filename.replace('.png', '').split('_')
        
        if len(parts) >= 3:
            if parts[0] == 'design':
                category = parts[1]
                # Join remaining parts (except timestamp) as theme
                theme_parts = parts[2:-2] if len(parts) > 4 else parts[2:-1]
                theme = ' '.join(theme_parts).replace('_', ' ')
                return category, theme
        
        # Default fallback
        return "custom", filename.replace('design_', '').replace('.png', '')
    
    def upload_to_printful(self, filepath, design_info):
        """Upload design to Printful"""
        if not PRINTFUL_API_KEY:
            print("  ❌ Printful API key not configured")
            return None
            
        headers = {
            "Authorization": f"Bearer {PRINTFUL_API_KEY.strip()}",
        }
        
        try:
            print("  📤 Uploading to Printful...")
            
            # Read image file
            with open(filepath, 'rb') as f:
                image_data = f.read()
            
            # Upload file
            files_url = f"{PRINTFUL_API_BASE}/files"
            files = {
                'file': (os.path.basename(filepath), image_data, 'image/png')
            }
            
            response = requests.post(
                files_url,
                headers=headers,
                files=files,
                data={'type': 'default'}
            )
            
            if response.status_code != 200:
                print(f"  ❌ Printful file upload failed: {response.status_code} - {response.text}")
                return None
                
            file_id = response.json()["result"]["id"]
            print(f"  ✅ File uploaded with ID: {file_id}")
            
            # Create product
            product_data = {
                "sync_product": {
                    "name": f"{design_info['category'].title()} - {design_info['theme'].title()}"
                },
                "sync_variants": [
                    {
                        "variant_id": 4012,  # S
                        "retail_price": f"{design_info['base_price']:.2f}",
                        "files": [{"id": file_id}]
                    },
                    {
                        "variant_id": 4013,  # M
                        "retail_price": f"{design_info['base_price']:.2f}",
                        "files": [{"id": file_id}]
                    },
                    {
                        "variant_id": 4014,  # L
                        "retail_price": f"{design_info['base_price']:.2f}",
                        "files": [{"id": file_id}]
                    },
                    {
                        "variant_id": 4015,  # XL
                        "retail_price": f"{design_info['base_price']:.2f}",
                        "files": [{"id": file_id}]
                    },
                    {
                        "variant_id": 4016,  # 2XL
                        "retail_price": f"{design_info['base_price'] * 1.12:.2f}",
                        "files": [{"id": file_id}]
                    }
                ]
            }
            
            # Create product
            if PRINTFUL_STORE_ID:
                product_url = f"{PRINTFUL_API_BASE}/store/{PRINTFUL_STORE_ID}/products"
            else:
                product_url = f"{PRINTFUL_API_BASE}/sync/products"
            
            response = requests.post(
                product_url,
                json=product_data,
                headers={**headers, "Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                print(f"  ❌ Printful product creation failed: {response.status_code}")
                return None
                
            product_id = response.json()["result"]["id"]
            print(f"  ✅ Printful product created: ID {product_id}")
            
            return {
                "printful_file_id": file_id,
                "printful_product_id": product_id
            }
            
        except Exception as e:
            print(f"  ❌ Printful error: {str(e)}")
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
            
            url = f"{SHOPIFY_API_BASE}/products.json"
            response = requests.post(url, json=product_data, headers=headers)
            
            if response.status_code != 201:
                print(f"  ❌ Shopify creation failed: {response.status_code}")
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
            if upload_info.get('printful_product_id'):
                print(f"   Printful ID: {upload_info['printful_product_id']}")
            if upload_info.get('shopify_product_id'):
                print(f"   Shopify ID: {upload_info['shopify_product_id']}")
            return False
        
        # Extract design information
        category, theme = self.extract_design_info(filename)
        
        design_info = {
            "filename": filename,
            "filepath": str(filepath),
            "file_hash": file_hash,
            "category": category,
            "theme": theme,
            "base_price": 25.00,
            "retail_price": 25.00 * MARKUP_PERCENT
        }
        
        print(f"📋 Category: {category}")
        print(f"🎨 Theme: {theme}")
        print(f"💰 Price: ${design_info['retail_price']:.2f}")
        
        if self.dry_run:
            print("🔍 DRY RUN - Would upload this file")
            return True
        
        # Upload to Printful
        printful_result = None
        if PRINTFUL_API_KEY:
            printful_result = self.upload_to_printful(filepath, design_info)
        
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
                "theme": theme
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
                    time.sleep(2)  # Rate limiting
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

def main():
    parser = argparse.ArgumentParser(
        description='Upload t-shirt designs to Printful and Shopify',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python upload_manager.py                    # Process current directory
  python upload_manager.py --dir ./designs    # Process specific directory
  python upload_manager.py --dry-run          # Test without uploading
  python upload_manager.py --file design.png  # Upload single file
  python upload_manager.py --retry-failed     # Retry failed uploads
        """
    )
    
    parser.add_argument(
        '--dir',
        type=str,
        default='.',
        help='Directory containing design files (default: current directory)'
    )
    
    parser.add_argument(
        '--file',
        type=str,
        help='Upload a specific file'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be uploaded without actually uploading'
    )
    
    parser.add_argument(
        '--retry-failed',
        action='store_true',
        help='Retry previously failed uploads'
    )
    
    parser.add_argument(
        '--reset-tracker',
        action='store_true',
        help='Reset upload tracker (WARNING: will re-upload everything)'
    )
    
    args = parser.parse_args()
    
    # Reset tracker if requested
    if args.reset_tracker:
        if input("Are you sure you want to reset the tracker? (yes/no): ").lower() == 'yes':
            if os.path.exists(UPLOAD_TRACKER_FILE):
                os.remove(UPLOAD_TRACKER_FILE)
                print("Tracker reset!")
        return
    
    # Create upload manager
    manager = UploadManager(upload_dir=args.dir, dry_run=args.dry_run)
    
    # Process single file or directory
    if args.file:
        filepath = Path(args.file)
        if filepath.exists():
            manager.process_file(filepath)
        else:
            print(f"File not found: {args.file}")
    else:
        # Retry failed if requested
        if args.retry_failed:
            print("Retrying failed uploads...")
            for file_hash, info in manager.tracker["failed"].items():
                filepath = Path(info["filename"])
                if filepath.exists():
                    # Remove from failed tracker
                    del manager.tracker["failed"][file_hash]
                    manager.save_tracker()
                    # Try again
                    manager.process_file(filepath)
        else:
            manager.process_directory()

if __name__ == "__main__":
    main()
