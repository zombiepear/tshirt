#!/usr/bin/env python3
"""
Working Printful T-Shirt Generator
Fixes common API issues and includes comprehensive debugging
"""

import os
import json
import random
import logging
import requests
import base64
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from openai import OpenAI

# Configure logging with detailed formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('tshirt_generator.log')
    ]
)
logger = logging.getLogger(__name__)

class WorkingPrintfulGenerator:
    def __init__(self):
        """Initialize with proper API configurations."""
        # API Keys from environment
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.printful_api_token = os.getenv('PRINTFUL_API_TOKEN')  # OAuth Bearer token
        self.shopify_api_key = os.getenv('SHOPIFY_API_KEY')
        self.shopify_password = os.getenv('SHOPIFY_PASSWORD')
        self.shopify_store_name = os.getenv('SHOPIFY_STORE_NAME')
        
        if not all([self.openai_api_key, self.printful_api_token]):
            raise ValueError("Missing required API keys")
        
        # Initialize OpenAI
        self.openai_client = OpenAI(api_key=self.openai_api_key)
        
        # Printful configuration
        self.printful_base_url = "https://api.printful.com"
        self.printful_headers = {
            "Authorization": f"Bearer {self.printful_api_token}",
            "Content-Type": "application/json",
            "User-Agent": "TShirtGenerator/1.0"
        }
        
        # Valid Bella+Canvas 3001 variant IDs (verified from API docs)
        self.bella_canvas_variants = {
            'white_s': 4011,
            'white_m': 4012, 
            'white_l': 4013,
            'white_xl': 4014,
            'black_s': 4016,
            'black_m': 4017,
            'black_l': 4018,
            'black_xl': 4019
        }
        
        # Load design collections
        self.collections = self._load_collections()
        
        # Verify Printful store setup
        self._verify_printful_store()
    
    def _load_collections(self) -> Dict:
        """Load design collections from file."""
        try:
            if os.path.exists('collections.json'):
                with open('collections.json', 'r') as f:
                    collections = json.load(f)
                logger.info(f"✅ Loaded {len(collections)} collections")
                return collections
            else:
                logger.warning("⚠️ No collections.json found, using default collection")
                return {
                    "birthday-party": {
                        "theme": "Birthday party t-shirt design, cake, balloons, party hats, funny age jokes, birthday wishes",
                        "title": "Birthday Celebrations",
                        "tags": ["birthday", "party", "celebration", "fun"]
                    }
                }
        except Exception as e:
            logger.error(f"❌ Error loading collections: {e}")
            return {}
    
    def _verify_printful_store(self) -> None:
        """Verify Printful store configuration and API access."""
        try:
            # Test API access
            response = requests.get(
                f"{self.printful_base_url}/store",
                headers=self.printful_headers,
                timeout=30
            )
            
            if response.status_code == 200:
                store_data = response.json()
                logger.info("✅ Printful API access verified")
                
                # Check store platform
                if 'result' in store_data:
                    platform = store_data['result'].get('platform')
                    store_name = store_data['result'].get('name', 'Unknown')
                    
                    logger.info(f"📋 Store: {store_name}")
                    logger.info(f"📋 Platform: {platform}")
                    
                    # Critical check: Must be Manual Order/API platform
                    if platform and platform.lower() not in ['api', 'manual']:
                        logger.error(f"❌ CRITICAL: Store platform is '{platform}'")
                        logger.error("❌ Product creation only works with 'Manual Order/API' platform stores")
                        logger.error("❌ Please create a new store in Printful dashboard:")
                        logger.error("❌ 1. Go to Stores → Add Store")
                        logger.error("❌ 2. Select 'Manual Order Platform / API'")
                        logger.error("❌ 3. Generate new OAuth token for that store")
                        raise ValueError(f"Invalid store platform: {platform}")
                    else:
                        logger.info("✅ Store platform is compatible with API")
                        
            else:
                logger.error(f"❌ Printful API access failed: {response.status_code}")
                logger.error(f"❌ Response: {response.text}")
                raise ValueError("Printful API access failed")
                
        except requests.RequestException as e:
            logger.error(f"❌ Network error verifying Printful store: {e}")
            raise
    
    def generate_design(self, collection_info: Dict) -> Optional[Dict]:
        """Generate design using OpenAI DALL-E 3."""
        try:
            # Create detailed prompt
            prompt = f"""
            Create a modern, trendy t-shirt design for: {collection_info['theme']}
            
            Style requirements:
            - Clean, professional design suitable for print-on-demand
            - Bold, eye-catching visuals
            - Suitable for both white and black t-shirts
            - High contrast elements
            - No copyrighted characters or brands
            - Modern, appealing to young adults
            - Centered design that works well on a t-shirt
            
            Make it vibrant and engaging!
            """
            
            logger.info("🎨 Generating design with OpenAI...")
            
            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                response_format="b64_json",
                n=1
            )
            
            # Extract base64 image data
            image_b64 = response.data[0].b64_json
            image_data = base64.b64decode(image_b64)
            
            logger.info("✅ Design generated successfully")
            
            return {
                'title': collection_info['title'],
                'image_data': image_data,
                'tags': collection_info.get('tags', [])
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating design: {e}")
            return None
    
    def upload_to_printful(self, image_data: bytes, filename: str) -> Optional[Dict]:
        """Upload image to Printful with comprehensive error handling."""
        try:
            logger.info("📤 Uploading image to Printful...")
            
            # Prepare file upload
            files = {
                'file': (filename, image_data, 'image/png')
            }
            
            # Upload headers (no Content-Type for multipart)
            upload_headers = {
                "Authorization": f"Bearer {self.printful_api_token}",
                "User-Agent": "TShirtGenerator/1.0"
            }
            
            response = requests.post(
                f"{self.printful_base_url}/files",
                headers=upload_headers,
                files=files,
                timeout=60
            )
            
            logger.info(f"📊 Upload response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Image uploaded successfully to Printful")
                logger.info(f"📋 File ID: {result['result']['id']}")
                return result
            else:
                logger.error(f"❌ Upload failed: {response.status_code}")
                logger.error(f"❌ Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Exception during upload: {e}")
            return None
    
    def create_printful_product(self, design_info: Dict, file_response: Dict) -> Optional[Dict]:
        """Create Printful product with correct API structure."""
        try:
            logger.info("🛍️ Creating Printful product...")
            
            # Extract file ID from upload response
            file_id = file_response['result']['id']
            logger.info(f"📋 Using file ID: {file_id}")
            
            # Create product payload with correct structure
            product_data = {
                "sync_product": {
                    "name": design_info['title'],
                    "external_id": f"TSHIRT_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                },
                "sync_variants": []
            }
            
            # Add variants for different sizes (start with just white shirts)
            white_variants = ['white_s', 'white_m', 'white_l']
            
            for variant_key in white_variants:
                variant_id = self.bella_canvas_variants[variant_key]
                
                variant_data = {
                    "variant_id": variant_id,
                    "retail_price": "25.00",  # String format required
                    "files": [
                        {
                            "id": file_id,
                            "type": "front_large"  # Updated placement name
                        }
                    ]
                }
                product_data["sync_variants"].append(variant_data)
            
            logger.info(f"📋 Creating product with {len(product_data['sync_variants'])} variants")
            
            # Make API request
            response = requests.post(
                f"{self.printful_base_url}/store/products",
                headers=self.printful_headers,
                json=product_data,  # Use json parameter, not data
                timeout=60
            )
            
            logger.info(f"📊 Product creation response: {response.status_code}")
            
            if response.status_code in [200, 201]:
                result = response.json()
                product_id = result['result']['id']
                logger.info(f"✅ Printful product created successfully! ID: {product_id}")
                return result
            else:
                logger.error(f"❌ Product creation failed: {response.status_code}")
                try:
                    error_data = response.json()
                    logger.error(f"❌ Error details: {json.dumps(error_data, indent=2)}")
                    
                    # Check for common errors
                    if 'Manual Order' in response.text:
                        logger.error("❌ STORE PLATFORM ERROR: This store is not set up for API product creation")
                        logger.error("❌ Please create a 'Manual Order/API' platform store in Printful")
                    
                except:
                    logger.error(f"❌ Raw response: {response.text}")
                
                return None
                
        except Exception as e:
            logger.error(f"❌ Exception creating product: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return None
    
    def create_shopify_product(self, design_info: Dict, printful_product: Dict) -> Optional[str]:
        """Create Shopify product (if configured)."""
        if not all([self.shopify_api_key, self.shopify_password, self.shopify_store_name]):
            logger.info("⚠️ Shopify not configured, skipping...")
            return None
        
        try:
            logger.info("🛒 Creating Shopify product...")
            
            # Shopify API configuration
            shopify_url = f"https://{self.shopify_store_name}.myshopify.com/admin/api/2023-04/products.json"
            shopify_auth = (self.shopify_api_key, self.shopify_password)
            
            # Create product data
            product_data = {
                "product": {
                    "title": design_info['title'],
                    "body_html": f"<p>Unique {design_info['title']} design</p>",
                    "vendor": "AI Designs",
                    "product_type": "T-Shirt",
                    "tags": ", ".join(design_info.get('tags', [])),
                    "variants": [
                        {
                            "option1": "Small",
                            "price": "25.00",
                            "sku": f"{design_info['title']}-S".replace(' ', '-'),
                            "inventory_management": "shopify",
                            "inventory_quantity": 100
                        }
                    ]
                }
            }
            
            response = requests.post(
                shopify_url,
                auth=shopify_auth,
                json=product_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 201:
                result = response.json()
                product_id = result['product']['id']
                logger.info(f"✅ Shopify product created: {product_id}")
                return str(product_id)
            else:
                logger.error(f"❌ Shopify creation failed: {response.status_code}")
                logger.error(f"❌ Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating Shopify product: {e}")
            return None
    
    def run_daily_generation(self) -> None:
        """Run the complete daily generation process."""
        try:
            logger.info("🚀 Starting daily t-shirt generation...")
            
            if not self.collections:
                logger.error("❌ No collections available")
                return
            
            # Select random collection
            collection_key = random.choice(list(self.collections.keys()))
            collection_info = self.collections[collection_key]
            
            logger.info(f"🎯 Selected collection: {collection_key}")
            logger.info(f"🎨 Theme: {collection_info['theme']}")
            
            # Generate design
            design_info = self.generate_design(collection_info)
            if not design_info:
                logger.error("❌ Failed to generate design")
                return
            
            # Create filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{design_info['title'].replace(' ', '_')}_{timestamp}.png"
            
            # Upload to Printful
            file_response = self.upload_to_printful(design_info['image_data'], filename)
            if not file_response:
                logger.error("❌ Failed to upload to Printful")
                return
            
            # Create Printful product
            printful_product = self.create_printful_product(design_info, file_response)
            if not printful_product:
                logger.error("❌ Failed to create Printful product")
                return
            
            # Create Shopify product (optional)
            shopify_product_id = self.create_shopify_product(design_info, printful_product)
            
            # Success summary
            logger.info("🎉 ===== GENERATION COMPLETE =====")
            logger.info(f"✅ Design: {design_info['title']}")
            logger.info(f"✅ Collection: {collection_key}")
            logger.info(f"✅ Printful Product ID: {printful_product['result']['id']}")
            if shopify_product_id:
                logger.info(f"✅ Shopify Product ID: {shopify_product_id}")
            logger.info("🎉 ================================")
            
        except Exception as e:
            logger.error(f"❌ Error in daily generation: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")

def main():
    """Main execution function."""
    try:
        generator = WorkingPrintfulGenerator()
        generator.run_daily_generation()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main()
