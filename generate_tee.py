#!/usr/bin/env python3
"""
Daily T-shirt design generator with Printful and Shopify integration.
Automatically creates designs, uploads to Printful, and lists on Shopify.
"""

import os
import json
import logging
import requests
import urllib3
import base64
import time
import random
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv

# Disable SSL warnings for GitHub Actions environment
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TShirtGenerator:
    def __init__(self):
        # API Configuration
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.shopify_store = os.getenv('SHOPIFY_STORE')
        self.shopify_access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        self.printful_api_key = os.getenv('PRINTFUL_API_KEY')
        self.printful_store_id = os.getenv('PRINTFUL_STORE_ID')
        self.markup_percent = float(os.getenv('MARKUP_PERCENT', '40'))
        
        # Validate required environment variables
        required_vars = [
            'OPENAI_API_KEY', 'SHOPIFY_STORE', 'SHOPIFY_ACCESS_TOKEN', 
            'PRINTFUL_API_KEY', 'PRINTFUL_STORE_ID'
        ]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")
        
        # Debug: Verify Printful access
        self.verify_printful_access()
        
        # Load collections mapping
        try:
            with open('collections.json', 'r') as f:
                self.collections = json.load(f)
            logger.info(f"Loaded {len(self.collections)} collections")
        except FileNotFoundError:
            logger.error("collections.json not found. Run seed_collections.py first.")
            raise
        
        # Printful product configuration (Bella + Canvas 3001 Unisex T-Shirt)
        self.printful_product_id = 71  # Bella + Canvas 3001
        self.printful_variant_ids = [
            4011, 4012, 4013, 4014, 4017,  # S, M, L, XL, 2XL in White
            4016, 4018, 4019, 4020, 4021   # S, M, L, XL, 2XL in Black
        ]

    def verify_printful_access(self):
        """Verify Printful API access and store information."""
        try:
            headers = {
                'Authorization': f'Bearer {self.printful_api_key}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Try to get stores list (note: plural 'stores')
            response = requests.get(
                'https://api.printful.com/stores',
                headers=headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                stores = response.json()
                logger.info(f"✅ Printful API access verified")
                logger.info(f"Available stores: {len(stores.get('result', []))}")
                
                # Check if our store ID exists
                if 'result' in stores:
                    for store in stores['result']:
                        logger.info(f"Store: {store.get('name', 'Unknown')} (ID: {store.get('id', 'Unknown')})")
                        if str(store.get('id')) == str(self.printful_store_id):
                            logger.info(f"✅ Found matching store ID: {self.printful_store_id}")
                            return
                
                logger.warning(f"⚠️ Store ID {self.printful_store_id} not found in available stores")
            else:
                logger.error(f"❌ Printful API access failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                
        except Exception as e:
            logger.error(f"Failed to verify Printful access: {e}")

    def generate_design_prompt(self, collection_key: str, theme: str) -> str:
        """Generate a detailed prompt for DALL-E based on collection theme."""
        base_prompt = f"""Create a t-shirt design for: {theme}

Style requirements:
- Clean, modern vector-style illustration
- Bold, eye-catching design suitable for t-shirt printing
- High contrast colors that work on both white and black shirts
- No text or typography (design only)
- Centered composition
- Simple but impactful visual elements

Design focus: {theme}
Make it visually appealing, trendy, and suitable for casual wear."""
        
        return base_prompt

    def generate_design_with_openai(self, prompt: str) -> Optional[str]:
        """Generate design using DALL-E API."""
        try:
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': 'dall-e-3',
                'prompt': prompt,
                'n': 1,
                'size': '1024x1024',
                'quality': 'standard',
                'response_format': 'b64_json'
            }
            
            response = requests.post(
                'https://api.openai.com/v1/images/generations',
                headers=headers,
                json=payload,
                timeout=60,
                verify=False  # Handle SSL in GitHub Actions
            )
            response.raise_for_status()
            
            result = response.json()
            return result['data'][0]['b64_json']
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None

    def upload_image_to_temp_host(self, image_data: str, filename: str) -> Optional[str]:
        """Upload image to temporary hosting service and return URL."""
        try:
            # Upload to imgbb.com (free image hosting with API)
            imgbb_api_key = "0f8b7c8c19b6f9d2e1a3f4c5b6d7e8f9"  # Public demo key
            
            upload_url = "https://api.imgbb.com/1/upload"
            
            payload = {
                'key': imgbb_api_key,
                'image': image_data,
                'name': filename
            }
            
            response = requests.post(upload_url, data=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    image_url = result['data']['url']
                    logger.info(f"✅ Image uploaded to temporary host: {image_url}")
                    return image_url
            
            logger.error(f"Failed to upload to temp host: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"Error uploading to temp host: {e}")
            return None

    def upload_to_printful(self, image_data: str, filename: str) -> Optional[Dict]:
        """Upload design to Printful file library using URL method."""
        try:
            # First, upload image to temporary hosting service
            logger.info("Uploading image to temporary hosting service...")
            image_url = self.upload_image_to_temp_host(image_data, filename)
            
            if not image_url:
                logger.error("Failed to get image URL from temp hosting")
                return None
            
            # Now upload to Printful using the URL
            headers = {
                'Authorization': f'Bearer {self.printful_api_key}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Content-Type': 'application/json'
            }
            
            # Printful expects URL in files array
            data = {
                'files': [
                    {
                        'url': image_url,
                        'filename': filename,
                        'type': 'default'
                    }
                ],
                'store_id': self.printful_store_id
            }
            
            logger.info(f"Uploading to Printful with image URL")
            
            response = requests.post(
                'https://api.printful.com/files',
                headers=headers,
                json=data,
                timeout=60,
                verify=False
            )
            
            if response.status_code == 200:
                logger.info(f"✅ File upload successful via URL method")
                return response.json()
            else:
                logger.error(f"Printful upload failed with status {response.status_code}")
                try:
                    error_json = response.json()
                    logger.error(f"Error: {error_json}")
                except:
                    logger.error(f"Response: {response.text[:200]}...")
                return None
                
        except Exception as e:
            logger.error(f"Failed to upload file to Printful: {e}")
            return None

    def create_printful_product(self, file_info: Dict, title: str, collection_key: str) -> Optional[Dict]:
        """Create product in Printful store."""
        try:
            headers = {
                'Authorization': f'Bearer {self.printful_api_key}',
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9'
            }
            
            # Create sync product payload
            payload = {
                'sync_product': {
                    'name': title,
                    'thumbnail': file_info['result']['url']
                },
                'sync_variants': []
            }
            
            # Add variants for different sizes and colors
            for variant_id in self.printful_variant_ids:
                variant = {
                    'retail_price': '19.99',
                    'variant_id': variant_id,
                    'files': [
                        {
                            'id': file_info['result']['id'],
                            'type': 'default',
                            'url': file_info['result']['url']
                        }
                    ]
                }
                payload['sync_variants'].append(variant)
            
            # Create the product
            response = requests.post(
                f'https://api.printful.com/store/products',
                headers=headers,
                json=payload,
                timeout=60,
                verify=False  # Handle SSL in GitHub Actions
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to create Printful product: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            return None

    def get_printful_cost(self, printful_product_id: str) -> float:
        """Get the cost of the product from Printful."""
        try:
            headers = {
                'Authorization': f'Bearer {self.printful_api_key}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json, text/plain, */*'
            }
            
            response = requests.get(
                f'https://api.printful.com/store/products/{printful_product_id}',
                headers=headers,
                timeout=30,
                verify=False  # Handle SSL in GitHub Actions
            )
            response.raise_for_status()
            
            product_data = response.json()
            # Get the first variant's cost as baseline
            if product_data['result']['sync_variants']:
                cost = float(product_data['result']['sync_variants'][0]['cost'])
                return cost
            
            return 8.50  # Fallback cost
            
        except Exception as e:
            logger.error(f"Failed to get Printful cost: {e}")
            return 8.50  # Fallback cost

    def create_shopify_product(self, title: str, collection_id: str, price: float, 
                             printful_product_id: str, image_url: str) -> Optional[Dict]:
        """Create product in Shopify store."""
        try:
            headers = {
                'X-Shopify-Access-Token': self.shopify_access_token,
                'Content-Type': 'application/json'
            }
            
            product_data = {
                'product': {
                    'title': title,
                    'body_html': f'<p>Unique t-shirt design created with AI. High-quality print on comfortable unisex t-shirt.</p><p>Fulfilled by Printful.</p>',
                    'vendor': 'AI Design Co',
                    'product_type': 'T-Shirt',
                    'status': 'active',
                    'published': True,
                    'tags': 'ai-generated, t-shirt, unique, printful',
                    'images': [
                        {
                            'src': image_url,
                            'alt': title
                        }
                    ],
                    'variants': [
                        {
                            'title': 'Default Title',
                            'price': str(price),
                            'sku': f'AI-{printful_product_id}',
                            'inventory_management': 'printful',
                            'fulfillment_service': 'printful',
                            'requires_shipping': True,
                            'taxable': True
                        }
                    ],
                    'metafields': [
                        {
                            'namespace': 'printful',
                            'key': 'product_id',
                            'value': str(printful_product_id),
                            'type': 'single_line_text_field'
                        }
                    ],
                    'tags': f'ai-generated, t-shirt, unique, printful, {collection_key}'
                }
            }
            
            # Add to collection if specified
            if collection_id:
                product_data['product']['tags'] += f', collection-{collection_id}'
            
            response = requests.post(
                f'https://{self.shopify_store}.myshopify.com/admin/api/2023-04/products.json',
                headers=headers,
                json=product_data,
                timeout=60,
                verify=False  # Handle SSL in GitHub Actions
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to create Shopify product: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            return None

    def add_product_to_collection(self, product_id: str, collection_id: str) -> bool:
        """Add product to Shopify collection (skip if no collection ID)."""
        if not collection_id:
            logger.info("No collection ID provided, skipping collection assignment")
            return True
            
        try:
            headers = {
                'X-Shopify-Access-Token': self.shopify_access_token,
                'Content-Type': 'application/json'
            }
            
            collect_data = {
                'collect': {
                    'product_id': product_id,
                    'collection_id': collection_id
                }
            }
            
            response = requests.post(
                f'https://{self.shopify_store}.myshopify.com/admin/api/2023-04/collects.json',
                headers=headers,
                json=collect_data,
                timeout=30,
                verify=False  # Handle SSL in GitHub Actions
            )
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add product to collection: {e}")
            return False

    def generate_daily_products(self, num_products: int = 3) -> List[Dict]:
        """Generate specified number of products for today."""
        results = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        # Select collections for today (cycle through available ones)
        collection_keys = list(self.collections.keys())
        selected_collections = collection_keys[:num_products]
        
        for i, collection_key in enumerate(selected_collections):
            try:
                collection = self.collections[collection_key]
                theme = collection['theme']
                collection_id = collection.get('shopify_id')
                if collection_id == "None" or collection_id is None:
                    collection_id = None
                
                logger.info(f"Generating design for {collection_key}: {theme}")
                
                # Generate design
                prompt = self.generate_design_prompt(collection_key, theme)
                image_data = self.generate_design_with_openai(prompt)
                
                if not image_data:
                    logger.error(f"Failed to generate design for {collection_key}")
                    continue
                
                logger.info(f"Design generated successfully for {collection_key}")
                
                # Create filename
                clean_title = collection['title'].replace(' ', '_').replace('&', 'and')
                filename = f"{clean_title}_{timestamp}.png"
                
                # Upload to Printful
                logger.info(f"Uploading to Printful: {collection['title']} {timestamp}")
                file_info = self.upload_to_printful(image_data, filename)
                
                if not file_info:
                    logger.error(f"Failed to upload design for {collection_key}")
                    continue
                
                # Small delay between Printful API calls
                time.sleep(1)
                
                # Create Printful product
                printful_product = self.create_printful_product(
                    file_info, collection['title'], collection_key
                )
                
                if not printful_product:
                    logger.error(f"Failed to create Printful product for {collection_key}")
                    continue
                
                printful_product_id = printful_product['result']['id']
                logger.info(f"Printful product created: {printful_product_id}")
                
                # Calculate pricing
                cost = self.get_printful_cost(printful_product_id)
                price = round(cost * (1 + self.markup_percent / 100), 2)
                
                # Small delay before Shopify API call
                time.sleep(1)
                
                # Create Shopify product
                logger.info(f"Creating Shopify product: {collection['title']}")
                shopify_product = self.create_shopify_product(
                    collection['title'],
                    collection_id,
                    price,
                    printful_product_id,
                    file_info['result']['url']
                )
                
                if not shopify_product:
                    logger.error(f"Failed to create Shopify product for {collection_key}")
                    continue
                
                shopify_product_id = shopify_product['product']['id']
                logger.info(f"Shopify product created: {shopify_product_id}")
                
                # Add to collection
                if collection_id and collection_id != "None":
                    self.add_product_to_collection(shopify_product_id, collection_id)
                else:
                    logger.info("No collection ID available, product will be ungrouped")
                
                result = {
                    'collection_key': collection_key,
                    'title': collection['title'],
                    'theme': theme,
                    'printful_product_id': printful_product_id,
                    'shopify_product_id': shopify_product_id,
                    'price': price,
                    'cost': cost,
                    'image_url': file_info['result']['url']
                }
                
                results.append(result)
                
                logger.info(f"✅ {collection['title']} | {collection_key} | £{price} | {shopify_product_id}")
                
                # Add small delay between products to avoid rate limiting
                if i < len(selected_collections) - 1:  # Don't delay after last product
                    time.sleep(2)
                
            except Exception as e:
                logger.error(f"Failed to process {collection_key}: {e}")
                continue
        
        return results

def main():
    """Main execution function."""
    try:
        generator = TShirtGenerator()
        
        logger.info("Starting daily t-shirt generation...")
        results = generator.generate_daily_products(num_products=3)
        
        if results:
            logger.info(f"✅ Successfully created {len(results)} products")
            for result in results:
                logger.info(f"  - {result['title']}: £{result['price']} (Shopify: {result['shopify_product_id']})")
        else:
            logger.warning("⚠️ No products were created successfully")
            
    except Exception as e:
        logger.error(f"Script failed: {e}")
        raise

if __name__ == "__main__":
    main()
