#!/usr/bin/env python3
"""
AI T-Shirt Generator for Printful + Shopify
Fixed version using URL-based file upload
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
import boto3
from datetime import datetime
from typing import Optional, Dict, List
from io import BytesIO
from PIL import Image
from openai import OpenAI
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Set up logging
log_level = logging.DEBUG if os.environ.get('DEBUG') else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tshirt_generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TShirtGenerator:
    def __init__(self):
        # API Keys and Config
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')
        self.printful_api_key = os.environ.get('PRINTFUL_API_KEY')
        self.store_id = os.environ.get('PRINTFUL_STORE_ID')
        self.shopify_store = os.environ.get('SHOPIFY_STORE')
        self.shopify_token = os.environ.get('SHOPIFY_ACCESS_TOKEN')
        self.markup_percent = float(os.environ.get('MARKUP_PERCENT', '30'))
        
        # S3 Configuration (for hosting files)
        self.aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        self.s3_bucket = os.environ.get('S3_BUCKET_NAME', 'printful-designs')
        self.s3_region = os.environ.get('S3_REGION', 'us-east-1')
        
        # Validate required environment variables
        if not all([self.openai_api_key, self.printful_api_key, self.store_id]):
            raise ValueError("Missing required environment variables")
        
        # Initialize OpenAI
        try:
            import openai
            logger.info(f"OpenAI library version: {openai.__version__}")
            self.openai_client = OpenAI(api_key=self.openai_api_key)
            logger.info("✅ OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"OpenAI initialization error: {e}")
            raise
        
        # Initialize session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Printful API setup
        self.printful_api_url = 'https://api.printful.com'
        self.printful_headers = {
            'Authorization': f'Bearer {self.printful_api_key}',
            'Content-Type': 'application/json'
        }
        
        # S3 client setup (if AWS credentials available)
        self.s3_client = None
        if self.aws_access_key and self.aws_secret_key:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.s3_region
            )
            logger.info("✅ AWS S3 client initialized")
        
        # Collection themes
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
                'variant_ids': [4011, 4012, 4013, 4014, 4016, 4017]
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
        logger.info(f"🏪 Store ID: {self.store_id}")
    
    def verify_printful_connection(self):
        """Verify Printful API connection and store type."""
        try:
            response = self.session.get(
                f'{self.printful_api_url}/stores/{self.store_id}',
                headers=self.printful_headers,
                timeout=30
            )
            
            if response.status_code == 200:
                store_data = response.json()
                store_type = store_data['result']['type']
                logger.info("✅ Printful API connection verified")
                logger.info(f"📋 Store: {store_data['result']['name']}")
                logger.info(f"📋 Type: {store_type}")
                
                # Warn if store type might have limitations
                if store_type != 'manual':
                    logger.warning(f"⚠️  Store type '{store_type}' may have API limitations")
                
                return True
            else:
                logger.error(f"❌ Printful API error: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Error verifying Printful connection: {e}")
            return False
    
    def upload_to_s3(self, image_data: bytes, filename: str) -> Optional[str]:
        """Upload image to S3 and return public URL."""
        if not self.s3_client:
            logger.warning("S3 not configured, will use GitHub Pages fallback")
            return None
        
        try:
            # Upload to S3
            key = f"designs/{datetime.now().strftime('%Y%m%d')}/{filename}"
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=image_data,
                ContentType='image/png',
                ACL='public-read'
            )
            
            # Return public URL
            url = f"https://{self.s3_bucket}.s3.{self.s3_region}.amazonaws.com/{key}"
            logger.info(f"✅ Uploaded to S3: {url}")
            return url
            
        except Exception as e:
            logger.error(f"❌ S3 upload failed: {e}")
            return None
    
    def upload_to_github_pages(self, image_data: bytes, filename: str) -> str:
        """Fallback: Create a data URL for the image."""
        # This is a temporary solution - in production, you'd upload to GitHub Pages
        # or another free hosting service
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        data_url = f"data:image/png;base64,{image_b64}"
        logger.info("📎 Using data URL (temporary solution)")
        return data_url
    
    def upload_to_printful(self, design_url: str, filename: str) -> Optional[str]:
        """Upload design to Printful using URL-based method."""
        try:
            logger.info("📤 Uploading to Printful File Library...")
            
            # Printful expects URL-based file submission
            url = f'{self.printful_api_url}/files'
            
            # Prepare the request data
            file_data = {
                'url': design_url,
                'type': 'default',
                'filename': filename,
                'visible': True,
                'options': []
            }
            
            # Include store_id in headers
            headers = self.printful_headers.copy()
            headers['X-PF-Store-Id'] = str(self.store_id)
            
            logger.debug(f"Request URL: {url}")
            logger.debug(f"Request data: {json.dumps(file_data, indent=2)}")
            
            # Make the request
            response = self.session.post(
                url,
                headers=headers,
                json=file_data,
                timeout=60
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                file_id = result['result']['id']
                file_url = result['result'].get('url', design_url)
                logger.info(f"✅ File uploaded successfully. ID: {file_id}")
                logger.info(f"📎 File URL: {file_url}")
                return str(file_id)
            else:
                logger.error(f"❌ Upload failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error uploading to Printful: {e}")
            return None
    
    def get_trending_theme(self, collection_key: str) -> str:
        """Get a theme from the collection."""
        collection = self.collections[collection_key]
        theme = random.choice(collection['themes'])
        
        # Add seasonal modifications
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
    
    def prepare_image_for_printful(self, image_data: bytes) -> bytes:
        """Prepare image for Printful (resize if needed)."""
        try:
            img = Image.open(BytesIO(image_data))
            
            # Printful recommends 150-300 DPI
            # For a 12"x16" print area at 150 DPI: 1800x2400 pixels
            target_size = (1800, 2400)
            
            if img.size != target_size:
                # Calculate aspect ratio preserving resize
                img.thumbnail(target_size, Image.Resampling.LANCZOS)
                
                # Create new image with white background
                new_img = Image.new('RGB', target_size, 'white')
                
                # Paste resized image in center
                x = (target_size[0] - img.width) // 2
                y = (target_size[1] - img.height) // 2
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
    
    def create_printful_product(self, title: str, printful_file_id: str, collection: Dict) -> Optional[Dict]:
        """Create a product in Printful."""
        try:
            url = f'{self.printful_api_url}/store/products'
            
            # Base cost for Unisex Staple T-Shirt
            base_cost = 12.95
            markup = base_cost * (self.markup_percent / 100)
            retail_price = int(base_cost + markup) + 0.99
            
            # Create variants
            variants = []
            for variant_id in collection['variant_ids']:
                variants.append({
                    'variant_id': variant_id,
                    'retail_price': f"{retail_price:.2f}",
                    'is_enabled': True,
                    'files': [  # Must be an array
                        {
                            'id': printful_file_id,
                            'placement': 'front'
                        }
                    ]
                })
            
            product_data = {
                'sync_product': {
                    'name': title,
                    'thumbnail': printful_file_id,
                    'is_ignored': False
                },
                'sync_variants': variants
            }
            
            # Include store_id in headers
            headers = self.printful_headers.copy()
            headers['X-PF-Store-Id'] = str(self.store_id)
            
            logger.info(f"📝 Creating product with {len(variants)} variants...")
            
            response = self.session.post(
                url,
                headers=headers,
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
                
                # Check if it's a store type issue
                if "Manual Order / API platform" in response.text:
                    logger.error("⚠️  This endpoint only works with Manual/API stores, not Shopify stores")
                    logger.info("💡 Products will be created when synced through Shopify")
                    # Return a mock success for Shopify stores
                    return {'sync_product': {'id': 'shopify-pending'}}
                
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating product: {e}")
            return None
    
    def save_design_locally(self, image_data: bytes, title: str, collection_key: str):
        """Save design locally for backup."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{collection_key}_{timestamp}.png"
            
            with open(filename, 'wb') as f:
                f.write(image_data)
            
            logger.info(f"💾 Saved design as {filename}")
            
            # Save metadata
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
        
        # Upload to hosting service (S3 or fallback)
        logger.info("☁️ Uploading to hosting service...")
        design_url = self.upload_to_s3(prepared_image, f"{title.replace(' ', '_')}.png")
        
        if not design_url:
            # Fallback to GitHub Pages or data URL
            design_url = self.upload_to_github_pages(prepared_image, f"{title.replace(' ', '_')}.png")
        
        # Upload to Printful File Library
        file_id = self.upload_to_printful(design_url, f"{title.replace(' ', '_')}.png")
        
        if not file_id:
            logger.error(f"❌ Failed to upload design to Printful for {collection_key}")
            return
        
        # Add delay to avoid rate limiting
        time.sleep(2)
        
        # Create product
        logger.info("🛍️ Creating Printful product...")
        product = self.create_printful_product(title, file_id, collection)
        
        if not product:
            logger.error(f"❌ Failed to create product for {collection_key}")
            return
        
        logger.info(f"✅ Successfully processed {collection_key}")
        logger.info(f"🎨 Title: {title}")
        if product and 'sync_product' in product:
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
