#!/usr/bin/env python3
"""
T-Shirt Generator for Printful and Shopify
Designed for GitHub Actions - uses environment variables from secrets
"""

import os
import json
import random
import logging
import requests
import base64
from datetime import datetime
from typing import Dict, List, Optional
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('tshirt_generator.log')
    ]
)
logger = logging.getLogger(__name__)

class TShirtGenerator:
    def __init__(self):
        """Initialize with environment variables from GitHub secrets."""
        # Get API keys from environment (set by GitHub Actions)
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')
        self.printful_api_key = os.environ.get('PRINTFUL_API_KEY')
        self.printful_store_id = os.environ.get('PRINTFUL_STORE_ID')
        self.shopify_store = os.environ.get('SHOPIFY_STORE')
        self.shopify_access_token = os.environ.get('SHOPIFY_ACCESS_TOKEN')
        self.markup_percent = float(os.environ.get('MARKUP_PERCENT', '1.4'))
        
        # Validate required keys
        if not self.openai_api_key:
            raise ValueError("Missing OPENAI_API_KEY in environment")
        if not self.printful_api_key:
            raise ValueError("Missing PRINTFUL_API_KEY in environment")
        
        # Initialize OpenAI
        self.openai_client = OpenAI(api_key=self.openai_api_key)
        
        # Printful configuration
        self.printful_base_url = "https://api.printful.com"
        self.printful_headers = {
            "Authorization": f"Bearer {self.printful_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "TShirtGenerator/1.0"
        }
        
        # Bella+Canvas 3001 variant IDs
        self.variant_mapping = {
            'white_s': 4011,
            'white_m': 4012,
            'white_l': 4013,
            'white_xl': 4014,
            'white_2xl': 4015,
            'black_s': 4016,
            'black_m': 4017,
            'black_l': 4018,
            'black_xl': 4019,
            'black_2xl': 4020
        }
        
        # Load collections
        self.collections = self._load_collections()
        
        # Verify Printful connection
        self._verify_printful_connection()
    
    def _load_collections(self) -> Dict:
        """Load design collections from JSON file."""
        try:
            if os.path.exists('collections.json'):
                with open('collections.json', 'r') as f:
                    collections = json.load(f)
                logger.info(f"✅ Loaded {len(collections)} collections")
                return collections
            else:
                logger.warning("⚠️ collections.json not found, using default")
                return {
                    "general": {
                        "name": "General Designs",
                        "title": "Unique T-Shirt Design",
                        "theme": "Creative and unique t-shirt design, modern, trendy, appealing to young adults",
                        "tags": ["unique", "creative", "modern"]
                    }
                }
        except Exception as e:
            logger.error(f"❌ Error loading collections: {e}")
            return {
                "general": {
                    "name": "General Designs",
                    "title": "AI T-Shirt Design",
                    "theme": "Creative and unique t-shirt design",
                    "tags": ["creative", "unique", "ai"]
                }
            }
    
    def _verify_printful_connection(self) -> None:
        """Verify Printful API access."""
        try:
            # First, try to get the store with store_id if available
            if self.printful_store_id:
                url = f"{self.printful_base_url}/stores/{self.printful_store_id}"
            else:
                # Try to get all stores and use the first one
                url = f"{self.printful_base_url}/stores"
            
            response = requests.get(
                url,
                headers=self.printful_headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Printful API connection verified")
                
                if 'result' in data:
                    store_info = data['result']
                    logger.info(f"📋 Store: {store_info.get('name', 'Unknown')}")
                    logger.info(f"📋 Type: {store_info.get('type', 'Unknown')}")
                    
                    # Store the store ID if not already set
                    if not self.printful_store_id and 'id' in store_info:
                        self.printful_store_id = store_info['id']
            else:
                logger.error(f"❌ Printful API error: {response.status_code}")
                logger.error(f"Response: {response.text}")
                
        except Exception as e:
            logger.error(f"❌ Failed to verify Printful connection: {e}")
    
    def generate_design(self, theme: str, title: str) -> Optional[Dict]:
        """Generate a T-shirt design using DALL-E 3."""
        try:
            prompt = f"""
            Create a professional t-shirt design for: {theme}
            
            Requirements:
            - Clean, eye-catching design suitable for print-on-demand
            - Works well on both white and black t-shirts
            - High contrast, bold elements
            - No text unless specifically requested
            - Modern, trendy style
            - Centered composition
            - No copyrighted content
            
            Make it vibrant and commercially appealing!
            """
            
            logger.info("🎨 Generating design with DALL-E 3...")
            
            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                response_format="b64_json",
                n=1
            )
            
            image_b64 = response.data[0].b64_json
            image_data = base64.b64decode(image_b64)
            
            logger.info("✅ Design generated successfully")
            
            return {
                'title': title,
                'image_data': image_data,
                'prompt': prompt
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating design: {e}")
            return None
    
    def upload_to_printful(self, image_data: bytes, filename: str) -> Optional[int]:
        """Upload image to Printful and return file ID."""
        try:
            logger.info("📤 Uploading to Printful...")
            
            files = {
                'file': (filename, image_data, 'image/png')
            }
            
            # Don't include Content-Type for multipart uploads
            headers = {
                "Authorization": f"Bearer {self.printful_api_key}",
                "User-Agent": "TShirtGenerator/1.0"
            }
            
            response = requests.post(
                f"{self.printful_base_url}/files",
                headers=headers,
                files=files,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                file_id = result['result']['id']
                logger.info(f"✅ Upload successful. File ID: {file_id}")
                return file_id
            else:
                logger.error(f"❌ Upload failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Upload exception: {e}")
            return None
    
    def create_printful_product(self, title: str, file_id: int, tags: List[str]) -> Optional[Dict]:
        """Create a product in Printful."""
        try:
            logger.info("🛍️ Creating Printful product...")
            
            # Ensure we have a store ID
            if not self.printful_store_id:
                logger.error("❌ No Printful store ID set")
                logger.error("❌ Please set PRINTFUL_STORE_ID in GitHub Secrets")
                return None
            
            # Calculate retail price based on cost and markup
            base_cost = 15.00  # Approximate base cost for Bella+Canvas 3001
            retail_price = round(base_cost * self.markup_percent, 2)
            
            # Create product data
            product_data = {
                "sync_product": {
                    "external_id": f"TSHIRT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "name": title
                },
                "sync_variants": []
            }
            
            # Add variants (white and black in common sizes)
            for color in ['white', 'black']:
                for size in ['s', 'm', 'l', 'xl']:
                    variant_key = f"{color}_{size}"
                    if variant_key in self.variant_mapping:
                        variant = {
                            "variant_id": self.variant_mapping[variant_key],
                            "retail_price": str(retail_price),
                            "files": [
                                {
                                    "id": file_id,
                                    "type": "default"  # Will be placed on front
                                }
                            ]
                        }
                        product_data["sync_variants"].append(variant)
            
            logger.info(f"📋 Creating product with {len(product_data['sync_variants'])} variants")
            
            response = requests.post(
                f"{self.printful_base_url}/stores/{self.printful_store_id}/products",
                headers=self.printful_headers,
                json=product_data,
                timeout=60
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                product_id = result['result']['id']
                logger.info(f"✅ Product created! ID: {product_id}")
                return result
            else:
                logger.error(f"❌ Product creation failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Product creation exception: {e}")
            return None
    
    def create_shopify_product(self, title: str, printful_product_id: int, tags: List[str]) -> Optional[str]:
        """Create product in Shopify if configured."""
        if not self.shopify_store or not self.shopify_access_token:
            logger.info("⚠️ Shopify not configured, skipping...")
            return None
        
        try:
            logger.info("🛒 Creating Shopify product...")
            
            # Shopify Admin API endpoint
            url = f"https://{self.shopify_store}.myshopify.com/admin/api/2024-01/products.json"
            
            headers = {
                "X-Shopify-Access-Token": self.shopify_access_token,
                "Content-Type": "application/json"
            }
            
            # Calculate price
            base_cost = 15.00
            retail_price = round(base_cost * self.markup_percent, 2)
            
            # Create product data
            product_data = {
                "product": {
                    "title": title,
                    "body_html": f"<p>Unique AI-generated design printed on premium Bella+Canvas 3001 t-shirts.</p>",
                    "vendor": "AI Designs",
                    "product_type": "T-Shirt",
                    "tags": ", ".join(tags),
                    "status": "active",
                    "variants": [
                        {
                            "option1": size.upper(),
                            "option2": color.capitalize(),
                            "price": str(retail_price),
                            "sku": f"{title.replace(' ', '-')}-{color}-{size}".upper(),
                            "inventory_management": None,  # Printful handles inventory
                            "fulfillment_service": "manual"
                        }
                        for color in ['White', 'Black']
                        for size in ['S', 'M', 'L', 'XL']
                    ],
                    "options": [
                        {
                            "name": "Size",
                            "values": ["S", "M", "L", "XL"]
                        },
                        {
                            "name": "Color",
                            "values": ["White", "Black"]
                        }
                    ]
                }
            }
            
            response = requests.post(url, headers=headers, json=product_data)
            
            if response.status_code == 201:
                result = response.json()
                product_id = result['product']['id']
                logger.info(f"✅ Shopify product created! ID: {product_id}")
                return str(product_id)
            else:
                logger.error(f"❌ Shopify creation failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Shopify exception: {e}")
            return None
    
    def generate_daily_designs(self, specific_categories: List[str] = None) -> None:
        """Generate designs for specified categories or random selection."""
        try:
            # Determine which categories to use
            if specific_categories:
                categories = [cat for cat in specific_categories if cat in self.collections]
                if not categories:
                    logger.error("❌ No valid categories specified")
                    return
            else:
                # Random selection
                categories = [random.choice(list(self.collections.keys()))]
            
            for category_key in categories:
                collection = self.collections[category_key]
                logger.info(f"\n🎯 Processing category: {category_key}")
                logger.info(f"📋 Collection: {collection.get('name', collection.get('title'))}")
                
                # Generate unique title for this design
                timestamp = datetime.now().strftime("%H%M%S")
                unique_title = f"{collection.get('title', 'AI Design')} #{timestamp}"
                
                # Generate design
                design = self.generate_design(
                    theme=collection.get('theme', ''),
                    title=unique_title
                )
                
                if not design:
                    logger.error(f"❌ Failed to generate design for {category_key}")
                    continue
                
                # Save image locally for artifact upload
                filename = f"{category_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                with open(filename, 'wb') as f:
                    f.write(design['image_data'])
                logger.info(f"💾 Saved design as {filename}")
                
                # Upload to Printful
                file_id = self.upload_to_printful(design['image_data'], filename)
                if not file_id:
                    logger.error(f"❌ Failed to upload design for {category_key}")
                    continue
                
                # Create Printful product
                printful_product = self.create_printful_product(
                    title=design['title'],
                    file_id=file_id,
                    tags=collection.get('tags', [])
                )
                
                if not printful_product:
                    logger.error(f"❌ Failed to create Printful product for {category_key}")
                    continue
                
                # Create Shopify product (optional)
                printful_id = printful_product['result']['id']
                shopify_id = self.create_shopify_product(
                    title=design['title'],
                    printful_product_id=printful_id,
                    tags=collection.get('tags', [])
                )
                
                # Success summary
                logger.info("\n🎉 === DESIGN COMPLETE ===")
                logger.info(f"✅ Category: {category_key}")
                logger.info(f"✅ Title: {design['title']}")
                logger.info(f"✅ Printful ID: {printful_id}")
                if shopify_id:
                    logger.info(f"✅ Shopify ID: {shopify_id}")
                logger.info("========================\n")
                
        except Exception as e:
            logger.error(f"❌ Error in daily generation: {e}")
            import traceback
            logger.error(traceback.format_exc())


def main():
    """Run a single generation cycle."""
    logger.info("🚀 Starting T-Shirt Generator")
    logger.info(f"📍 Running in: {'GitHub Actions' if os.environ.get('GITHUB_ACTIONS') else 'Local environment'}")
    
    try:
        generator = TShirtGenerator()
        generator.generate_daily_designs()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        exit(1)


if __name__ == "__main__":
    main()
