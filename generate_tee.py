#!/usr/bin/env python3
"""
AI T-Shirt Generator for Printful + Shopify
Generates unique designs daily using DALL-E 3
Enhanced with Cloudflare bypasses and robust error handling
"""

# FIX: Patch httpx before importing OpenAI
import httpx
_orig = httpx.Client.__init__
httpx.Client.__init__ = lambda s,**k: _orig(s,**{x:y for x,y in k.items() if x!='proxies'})

import os
import sys
import random
import requests
import json
import base64
import logging
import time
from datetime import datetime
from typing import Optional, Dict, List
from io import BytesIO
from PIL import Image
from openai import OpenAI
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tshirt_generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CloudflareBypassSession(requests.Session):
    """Enhanced session with Cloudflare bypass capabilities."""
    
    def __init__(self):
        super().__init__()
        
        # Set up retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.mount("http://", adapter)
        self.mount("https://", adapter)
        
        # Set realistic headers to avoid Cloudflare detection
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Referer': 'https://www.printful.com/',
            'Origin': 'https://www.printful.com'
        })

class TShirtGenerator:
    def __init__(self):
        # API Keys and Config
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')
        self.printful_api_key = os.environ.get('PRINTFUL_API_KEY')
        self.store_id = os.environ.get('PRINTFUL_STORE_ID')
        self.shopify_store = os.environ.get('SHOPIFY_STORE')
        self.shopify_token = os.environ.get('SHOPIFY_ACCESS_TOKEN')
        self.markup_percent = float(os.environ.get('MARKUP_PERCENT', '30'))
        
        # Validate required environment variables
        if not all([self.openai_api_key, self.printful_api_key, self.store_id]):
            raise ValueError("Missing required environment variables")
        
        # Initialize OpenAI with error handling for version compatibility
        try:
            # First, let's check the OpenAI version
            import openai
            logger.info(f"OpenAI library version: {openai.__version__}")
            
            # Try standard initialization
            self.openai_client = OpenAI(api_key=self.openai_api_key)
            logger.info("✅ OpenAI client initialized successfully")
        except TypeError as e:
            logger.error(f"OpenAI initialization error: {e}")
            if 'proxies' in str(e):
                logger.error("This is a known issue with OpenAI library > 1.12.0")
                logger.error("Please install OpenAI 1.12.0: pip install openai==1.12.0")
                raise ValueError("OpenAI library version incompatible. Need version 1.12.0")
            else:
                raise
        
        # Initialize session with Cloudflare bypass
        self.session = CloudflareBypassSession()
        
        # Printful API setup
        self.printful_api_url = 'https://api.printful.com'
        self.printful_headers = {
            'Authorization': f'Bearer {self.printful_api_key}',
            'Content-Type': 'application/json',
            'X-PF-Store-Id': self.store_id  # Some Printful endpoints prefer this
        }
        
        # Collection themes with Printful variant IDs
        self.collections = {
            'birthday-party': {
                'name': 'Birthday Celebrations',
                'themes': [
                    "Colorful birthday cake with candles and confetti",
                    "Party animals celebrating with balloons",
                    "Vintage birthday poster design",
                    "Neon birthday party vibes",
                    "Minimalist birthday celebration icons"
                ],
                'variant_ids': [4011, 4012, 4013, 4014, 4016, 4017]  # Unisex Staple T-Shirt
            },
            'retro-gaming': {
                'name': 'Retro Gaming',
                'themes': [
                    "8-bit pixel art game controller",
                    "Arcade cabinet with neon lights",
                    "Retro console collection pattern",
                    "Game over screen in vintage style",
                    "Pixelated space invaders battle"
                ],
                'variant_ids': [4011, 4012, 4013, 4014, 4016, 4017]
            },
            'nature-inspired': {
                'name': 'Nature Vibes',
                'themes': [
                    "Mountain landscape at sunset",
                    "Geometric forest pattern",
                    "Ocean waves in Japanese art style",
                    "Desert cactus garden illustration",
                    "Northern lights aurora design"
                ],
                'variant_ids': [4011, 4012, 4013, 4014, 4016, 4017]
            },
            'funny-slogans': {
                'name': 'Humor & Sarcasm',
                'themes': [
                    "Sarcastic coffee lover quote design",
                    "Programmer humor code snippet",
                    "Cat with attitude illustration",
                    "Dad joke championship winner badge",
                    "Introvert's survival guide diagram"
                ],
                'variant_ids': [4011, 4012, 4013, 4014, 4016, 4017]
            },
            'abstract-art': {
                'name': 'Abstract & Modern',
                'themes': [
                    "Liquid marble color flow",
                    "Geometric shapes in bold colors",
                    "Minimalist line art faces",
                    "Abstract brush strokes pattern",
                    "Bauhaus inspired composition"
                ],
                'variant_ids': [4011, 4012, 4013, 4014, 4016, 4017]
            }
        }
        
        logger.info(f"✅ Loaded {len(self.collections)} collections")
    
    def make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make a request with retry logic and Cloudflare handling."""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                # Add small random delay to appear more human
                time.sleep(random.uniform(0.5, 1.5))
                
                # Make the request
                response = self.session.request(method, url, **kwargs)
                
                # Check for Cloudflare challenge
                if response.status_code == 403 or "cf-ray" in response.headers:
                    logger.warning(f"Cloudflare challenge detected on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                
                return response
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise
        
        return response
    
    def verify_printful_connection(self):
        """Verify Printful API connection and get store info."""
        try:
            # Include store_id in the request
            response = self.make_request(
                'GET',
                f'{self.printful_api_url}/stores/{self.store_id}',
                headers=self.printful_headers,
                timeout=30
            )
            
            if response.status_code == 200:
                store_data = response.json()
                logger.info("✅ Printful API connection verified")
                logger.info(f"📋 Store: {store_data['result']['name']}")
                logger.info(f"📋 Type: {store_data['result']['type']}")
                return True
            else:
                logger.error(f"❌ Printful API error: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Error verifying Printful connection: {e}")
            return False
    
    def get_trending_theme(self, collection_key: str) -> str:
        """Get a theme from the collection."""
        collection = self.collections[collection_key]
        theme = random.choice(collection['themes'])
        
        # Add seasonal or trending modifications
        month = datetime.now().month
        if month == 12:
            theme += " with subtle Christmas elements"
        elif month in [6, 7, 8]:
            theme += " with summer vibes"
        elif month == 10:
            theme += " with Halloween twist"
        
        return theme
    
    def generate_title(self, theme: str, collection_name: str) -> str:
        """Generate a catchy title for the T-shirt."""
        # Use GPT to generate a title
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a creative t-shirt designer. Generate short, catchy product titles."},
                    {"role": "user", "content": f"Create a catchy t-shirt title (max 5 words) for this design theme: {theme}. Collection: {collection_name}"}
                ],
                max_tokens=20,
                temperature=0.8
            )
            
            title = response.choices[0].message.content.strip().strip('"')
            return title
        except Exception as e:
            logger.error(f"Error generating title: {e}")
            # Fallback title
            return f"{collection_name} Tee #{random.randint(100, 999)}"
    
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
            
            # Handle different OpenAI client scenarios
            if self.openai_client:
                response = self.openai_client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size="1024x1024",
                    quality="standard",
                    response_format="b64_json",
                    n=1
                )
                image_b64 = response.data[0].b64_json
            else:
                # Fallback for compatibility mode
                import openai
                response = openai.Image.create(
                    model="dall-e-3",
                    prompt=prompt,
                    size="1024x1024",
                    quality="standard",
                    response_format="b64_json",
                    n=1
                )
                image_b64 = response['data'][0]['b64_json']
            
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
    
    def prepare_image_for_printful(self, image_data: bytes) -> bytes:
        """Prepare image for Printful (resize if needed)."""
        try:
            img = Image.open(BytesIO(image_data))
            
            # Printful recommends 150-300 DPI
            # For a 12"x16" print area at 150 DPI: 1800x2400 pixels
            if img.size != (1800, 2400):
                # Calculate aspect ratio preserving resize
                img.thumbnail((1800, 2400), Image.Resampling.LANCZOS)
                
                # Create new image with white background
                new_img = Image.new('RGB', (1800, 2400), 'white')
                
                # Paste resized image in center
                x = (1800 - img.width) // 2
                y = (2400 - img.height) // 2
                new_img.paste(img, (x, y))
                
                img = new_img
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save to bytes
            output = BytesIO()
            img.save(output, format='PNG', optimize=True)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error preparing image: {e}")
            return image_data
    
    def upload_to_printful(self, image_data: bytes, filename: str) -> Optional[str]:
        """Upload design to Printful Files API."""
        try:
            # Include store_id in the URL path
            url = f'{self.printful_api_url}/files'
            
            # Prepare the file data
            files = {
                'file': (filename, BytesIO(image_data), 'image/png')
            }
            
            # For file uploads, create custom headers without Content-Type
            upload_headers = {
                'Authorization': f'Bearer {self.printful_api_key}',
                'X-PF-Store-Id': self.store_id,
                # Let requests set the Content-Type with boundary
            }
            
            # Add form data for store_id
            data = {
                'store_id': self.store_id
            }
            
            # Make the upload request with our custom session
            response = self.make_request(
                'POST',
                url,
                headers=upload_headers,
                files=files,
                data=data,
                timeout=60  # Longer timeout for file uploads
            )
            
            if response.status_code in [200, 201]:
                file_data = response.json()
                file_id = file_data['result']['id']
                file_url = file_data['result'].get('url', 'N/A')
                logger.info(f"✅ Upload successful. File ID: {file_id}")
                logger.info(f"📎 File URL: {file_url}")
                return file_id
            else:
                logger.error(f"❌ Upload failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                
                # Try to parse error details
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        logger.error(f"Error details: {error_data['error']}")
                except:
                    pass
                    
                return None
                
        except Exception as e:
            logger.error(f"❌ Error uploading to Printful: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            return None
    
    def calculate_price(self, base_cost: float) -> Dict[str, float]:
        """Calculate retail price with markup."""
        markup = base_cost * (self.markup_percent / 100)
        retail_price = base_cost + markup
        
        # Round to .99
        retail_price = int(retail_price) + 0.99
        
        return {
            'base_cost': base_cost,
            'markup': markup,
            'retail_price': retail_price
        }
    
    def create_printful_product(self, title: str, printful_file_id: str, collection: Dict) -> Optional[Dict]:
        """Create a product in Printful."""
        try:
            # Include store_id in the URL
            url = f'{self.printful_api_url}/store/products'
            
            # Base cost for Unisex Staple T-Shirt
            base_cost = 12.95
            pricing = self.calculate_price(base_cost)
            
            # Create variants for different sizes (simplified for now)
            variants = []
            
            # Map of variant IDs to sizes (these are example IDs, verify with Printful's catalog)
            variant_mapping = {
                4011: {'size': 'S', 'color': 'Black'},
                4012: {'size': 'M', 'color': 'Black'},
                4013: {'size': 'L', 'color': 'Black'},
                4014: {'size': 'XL', 'color': 'Black'},
                4016: {'size': '2XL', 'color': 'Black'},
                4017: {'size': '3XL', 'color': 'Black'}
            }
            
            for variant_id in collection['variant_ids']:
                if variant_id in variant_mapping:
                    variants.append({
                        'variant_id': variant_id,
                        'retail_price': f"{pricing['retail_price']:.2f}",
                        'is_enabled': True,
                        'files': [
                            {
                                'id': printful_file_id,
                                'placement': 'front'
                            }
                        ]
                    })
            
            product_data = {
                'store_id': int(self.store_id),
                'sync_product': {
                    'name': title,
                    'thumbnail': printful_file_id,
                    'is_ignored': False
                },
                'sync_variants': variants
            }
            
            logger.info(f"📝 Creating product with {len(variants)} variants...")
            
            response = self.make_request(
                'POST',
                url,
                headers=self.printful_headers,
                json=product_data,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info("✅ Product created successfully")
                return result['result']
            else:
                logger.error(f"❌ Product creation failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                
                # Try to parse error details
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        logger.error(f"Error details: {error_data['error']}")
                except:
                    pass
                    
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating product: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            return None
    
    def sync_to_shopify(self, product_id: str) -> bool:
        """Trigger Printful to sync product to Shopify."""
        try:
            # First, get the product to ensure it exists
            get_url = f'{self.printful_api_url}/store/products/{product_id}'
            
            response = self.make_request(
                'GET',
                get_url,
                headers=self.printful_headers,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"❌ Product not found: {product_id}")
                return False
            
            # Now sync it
            sync_url = f'{self.printful_api_url}/ecommerce/sync/products/{product_id}'
            
            sync_data = {
                'sync_product': {
                    'id': int(product_id)
                }
            }
            
            response = self.make_request(
                'POST',
                sync_url,
                headers=self.printful_headers,
                json=sync_data,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info("✅ Product sync initiated with Shopify")
                return True
            else:
                logger.error(f"❌ Sync failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error syncing to Shopify: {e}")
            return False
    
    def save_design_locally(self, image_data: bytes, title: str, collection_key: str):
        """Save design locally for backup."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{collection_key}_{timestamp}.png"
            
            with open(filename, 'wb') as f:
                f.write(image_data)
            
            logger.info(f"💾 Saved design as {filename}")
            
            # Also save metadata
            metadata = {
                'title': title,
                'collection': collection_key,
                'timestamp': timestamp,
                'filename': filename
            }
            
            with open(f"{collection_key}_{timestamp}_metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving design locally: {e}")
    
    def process_collection(self, collection_key: str):
        """Process a single collection."""
        logger.info(f"\n🎯 Processing category: {collection_key}")
        
        collection = self.collections[collection_key]
        logger.info(f"📋 Collection: {collection['name']}")
        
        # Get theme and generate title
        theme = self.get_trending_theme(collection_key)
        title = self.generate_title(theme, collection['name'])
        
        logger.info(f"🎯 Theme: {theme}")
        logger.info(f"📝 Title: {title}")
        
        # Generate design
        design = self.generate_design(theme, title)
        if not design:
            logger.error(f"❌ Failed to generate design for {collection_key}")
            return
        
        # Save locally first
        self.save_design_locally(design['image_data'], title, collection_key)
        
        # Prepare image for Printful
        logger.info("🖼️ Preparing image for Printful...")
        prepared_image = self.prepare_image_for_printful(design['image_data'])
        
        # Upload to Printful with retries
        logger.info("📤 Uploading to Printful...")
        file_id = self.upload_to_printful(
            prepared_image,
            f"{title.replace(' ', '_')}.png"
        )
        
        if not file_id:
            logger.error(f"❌ Failed to upload design for {collection_key}")
            return
        
        # Add delay to avoid rate limiting
        time.sleep(2)
        
        # Create product
        logger.info("🛍️ Creating Printful product...")
        product = self.create_printful_product(title, file_id, collection)
        
        if not product:
            logger.error(f"❌ Failed to create product for {collection_key}")
            return
        
        # Sync to Shopify if configured
        if self.shopify_store and self.shopify_token:
            product_id = product['sync_product']['id']
            logger.info("🔄 Syncing to Shopify...")
            time.sleep(2)  # Add delay before sync
            self.sync_to_shopify(product_id)
        
        logger.info(f"✅ Successfully processed {collection_key}")
        logger.info(f"🎨 Title: {title}")
        logger.info(f"🆔 Product ID: {product['sync_product']['id']}")
    
    def run_daily_generation(self):
        """Run the daily generation process."""
        logger.info("\n" + "="*50)
        logger.info("🚀 Starting Daily T-Shirt Generation")
        logger.info(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*50)
        
        # Log environment info
        logger.info(f"🔧 Store ID: {self.store_id}")
        logger.info(f"💰 Markup: {self.markup_percent}%")
        
        # Verify Printful connection first
        if not self.verify_printful_connection():
            logger.error("❌ Cannot proceed without Printful connection")
            return
        
        # Determine which collection to process
        # Use day of month to cycle through collections
        day_of_month = datetime.now().day
        collection_keys = list(self.collections.keys())
        collection_index = (day_of_month - 1) % len(collection_keys)
        collection_to_process = collection_keys[collection_index]
        
        logger.info(f"📊 Today's collection (day {day_of_month}): {collection_to_process}")
        
        # Process the selected collection
        self.process_collection(collection_to_process)
        
        logger.info("\n" + "="*50)
        logger.info("✅ Daily generation complete!")
        logger.info("="*50)

def main():
    """Main entry point."""
    try:
        # Log where we're running
        if os.environ.get('GITHUB_ACTIONS'):
            logger.info("📍 Running in: GitHub Actions")
            logger.info(f"🔧 Runner: {os.environ.get('RUNNER_NAME', 'Unknown')}")
            logger.info(f"🌍 Region: {os.environ.get('RUNNER_REGION', 'Unknown')}")
        else:
            logger.info("📍 Running in: Local environment")
        
        # Log Python version
        logger.info(f"🐍 Python version: {sys.version}")
        
        generator = TShirtGenerator()
        generator.run_daily_generation()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        logger.error("Traceback:", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
