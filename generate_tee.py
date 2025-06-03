#!/usr/bin/env python3
"""
T-Shirt Generator with GitHub Hosting (Using Raw URLs)
Fixed prompt to generate ONLY the design, not t-shirt mockups
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

class TShirtGenerator:
    def __init__(self):
        # API Keys and Config
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')
        self.printful_api_key = os.environ.get('PRINTFUL_API_KEY')
        self.store_id = os.environ.get('PRINTFUL_STORE_ID')
        self.shopify_store = os.environ.get('SHOPIFY_STORE')
        self.shopify_token = os.environ.get('SHOPIFY_ACCESS_TOKEN')
        self.markup_percent = float(os.environ.get('MARKUP_PERCENT', '30'))
        
        # GitHub configuration
        self.github_repo = os.environ.get('GITHUB_REPOSITORY', '')  # e.g., "username/repo"
        
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
        
        # Initialize session
        self.session = requests.Session()
        
        # Printful API setup
        self.printful_api_url = 'https://api.printful.com'
        self.printful_headers = {
            'Authorization': f'Bearer {self.printful_api_key}',
            'Content-Type': 'application/json',
            'X-PF-Store-Id': str(self.store_id)
        }
        
        # Collection themes with Printful variant IDs
        self.collections = {
            'birthday-party': {
                'name': 'Birthday Celebrations',
                'themes': [
                    "Colorful birthday cake with candles and confetti celebration",
                    "Party animals (cute cartoon animals) celebrating with balloons and party hats",
                    "Vintage retro birthday poster with ornate typography",
                    "Neon lights spelling out birthday wishes in 80s style",
                    "Minimalist birthday icons: cake, balloon, gift, confetti"
                ],
                'variant_ids': [4011, 4012, 4013, 4014, 4016, 4017]
            },
            'retro-gaming': {
                'name': 'Retro Gaming',
                'themes': [
                    "8-bit pixel art game controller floating in space with stars",
                    "Classic arcade cabinet with glowing screen and neon lights",
                    "Collection of retro gaming consoles arranged in a pattern",
                    "Pixelated 'Game Over' screen with coins and hearts",
                    "8-bit space invaders descending in formation"
                ],
                'variant_ids': [4011, 4012, 4013, 4014, 4016, 4017]
            },
            'nature-inspired': {
                'name': 'Nature Vibes',
                'themes': [
                    "Majestic mountain range silhouette at sunset with gradient sky",
                    "Geometric forest pattern with triangular trees and hidden animals",
                    "Ocean waves in traditional Japanese art style with foam details",
                    "Desert landscape with various cacti and succulents under starry sky",
                    "Northern lights aurora borealis swirling over pine forest"
                ],
                'variant_ids': [4011, 4012, 4013, 4014, 4016, 4017]
            },
            'funny-slogans': {
                'name': 'Humor & Sarcasm',
                'themes': [
                    "Grumpy coffee cup character with steam and attitude",
                    "Computer screen showing funny code comments and error messages",
                    "Sassy cat with sunglasses giving side-eye",
                    "Trophy or medal for 'World's Best Dad Jokes'",
                    "Introvert's battery meter showing low charge in crowds"
                ],
                'variant_ids': [4011, 4012, 4013, 4014, 4016, 4017]
            },
            'abstract-art': {
                'name': 'Abstract & Modern',
                'themes': [
                    "Liquid marble effect with swirling colors and gold veins",
                    "Bold geometric shapes overlapping in vibrant colors",
                    "Continuous line art drawing forming abstract faces",
                    "Paint brush strokes in rainbow colors on white background",
                    "Bauhaus-inspired composition with circles, squares, and triangles"
                ],
                'variant_ids': [4011, 4012, 4013, 4014, 4016, 4017]
            }
        }
        
        logger.info(f"✅ Loaded {len(self.collections)} collections")
        logger.info(f"🏪 Store ID: {self.store_id}")
        logger.info(f"📦 GitHub Repo: {self.github_repo}")
    
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
                
                if store_type == 'shopify':
                    logger.info("💡 Shopify store detected - products sync through Shopify")
                
                return True
            else:
                logger.error(f"❌ Printful API error: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Error verifying Printful connection: {e}")
            return False
    
    def get_github_url(self, filename: str) -> str:
        """Generate GitHub URL for the file - using RAW URLs for immediate access."""
        if self.github_repo:
            # Use raw GitHub URL - available IMMEDIATELY after push!
            return f"https://raw.githubusercontent.com/{self.github_repo}/main/designs/{filename}"
        else:
            # Fallback
            logger.warning("GitHub repo not set, using placeholder URL")
            return f"https://example.com/designs/{filename}"
    
    def save_design_locally(self, image_data: bytes, title: str, collection_key: str) -> str:
        """Save design locally and prepare for GitHub upload."""
        try:
            # Create designs directory
            os.makedirs("designs", exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{collection_key}_{timestamp}.png"
            filepath = os.path.join("designs", filename)
            
            # Save image
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            logger.info(f"💾 Saved design as {filepath}")
            
            # Save metadata
            metadata = {
                'title': title,
                'collection': collection_key,
                'timestamp': timestamp,
                'filename': filename,
                'github_url': self.get_github_url(filename)
            }
            
            metadata_path = os.path.join("designs", f"{collection_key}_{timestamp}_metadata.json")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return filename
                
        except Exception as e:
            logger.error(f"Error saving design locally: {e}")
            return None
    
    def upload_to_printful(self, design_url: str, filename: str) -> Optional[str]:
        """Upload design to Printful using URL-based method."""
        try:
            logger.info("📤 Uploading to Printful File Library...")
            logger.info(f"📎 URL: {design_url}")
            
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
            
            # Make the request
            response = self.session.post(
                url,
                headers=self.printful_headers,
                json=file_data,
                timeout=60
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                file_id = result['result']['id']
                file_url = result['result'].get('url', design_url)
                logger.info(f"✅ File uploaded successfully. ID: {file_id}")
                logger.info(f"📎 Printful URL: {file_url}")
                return str(file_id)
            else:
                logger.error(f"❌ Upload failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                
                if "file URL or data not specified" in response.text:
                    logger.error("💡 The file URL may not be accessible yet.")
                    logger.error("💡 Make sure the GitHub workflow has pushed the file.")
                
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
            theme += " with subtle Christmas holiday elements"
        elif month in [6, 7, 8]:
            theme += " with bright summer vibes"
        elif month == 10:
            theme += " with spooky Halloween elements"
        
        return theme
    
    def generate_title(self, theme: str, collection_name: str) -> str:
        """Generate a catchy title for the T-shirt."""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a creative t-shirt designer. Generate short, catchy product titles."},
                    {"role": "user", "content": f"Create ONE catchy t-shirt title (max 4 words) for this design theme: {theme}. Collection: {collection_name}. Just give me the title, no numbering or quotes."}
                ],
                max_tokens=20,
                temperature=0.8
            )
            
            title = response.choices[0].message.content.strip().strip('"').strip("'")
            # Clean up any numbering
            if title.startswith(('1.', '1)', '1 ')):
                title = title[2:].strip()
            return title
        except Exception as e:
            logger.error(f"Error generating title: {e}")
            return f"{collection_name} Tee #{random.randint(100, 999)}"
    
    def generate_design(self, theme: str, title: str) -> Optional[Dict]:
        """Generate a T-shirt design using DALL-E 3."""
        try:
            # FIXED PROMPT - No t-shirt mockups!
            prompt = f"""
            Create a graphic design for printing on a t-shirt. Theme: {theme}
            
            IMPORTANT Requirements:
            - Create ONLY the artwork/design itself, NOT a t-shirt or clothing mockup
            - The design should fill the entire square canvas
            - Style: Bold, eye-catching, suitable for t-shirt printing
            - High contrast with clear, defined edges
            - Works well on both light and dark fabric
            - Modern, trendy, commercially appealing aesthetic
            - Centered composition
            - No copyrighted characters or logos
            - No text unless specifically mentioned in the theme
            
            Design style: Professional print-ready artwork
            """
            
            logger.info("🎨 Generating design with DALL-E 3...")
            logger.info(f"Theme: {theme}")
            
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
                
                # Create new image with transparent background
                new_img = Image.new('RGBA', target_size, (255, 255, 255, 0))
                
                # Paste resized image in center
                x = (target_size[0] - img.width) // 2
                y = (target_size[1] - img.height) // 2
                
                # Convert to RGBA if needed for transparency
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                new_img.paste(img, (x, y), img)
                
                # Convert back to RGB for final save
                final_img = Image.new('RGB', target_size, (255, 255, 255))
                final_img.paste(new_img, (0, 0), new_img)
                img = final_img
            
            # Ensure RGB mode
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save to bytes
            output = BytesIO()
            img.save(output, format='PNG', optimize=True, quality=95)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error preparing image: {e}")
            return image_data
    
    def create_printful_product(self, title: str, printful_file_id: str, collection: Dict) -> Optional[Dict]:
        """Create a product in Printful."""
        try:
            url = f'{self.printful_api_url}/store/products'
            
            # Calculate pricing
            base_cost = 12.95
            markup = base_cost * (self.markup_percent / 100)
            retail_price = int(base_cost + markup) + 0.99
            
            # Create variants (simplified - just one size/color for now)
            variants = [{
                'variant_id': 4011,  # Unisex Staple T-Shirt - S - Black
                'retail_price': f"{retail_price:.2f}",
                'is_enabled': True,
                'files': [{
                    'id': printful_file_id,
                    'placement': 'front'
                }]
            }]
            
            product_data = {
                'sync_product': {
                    'name': title,
                    'thumbnail': printful_file_id,
                    'is_ignored': False
                },
                'sync_variants': variants
            }
            
            logger.info(f"📝 Creating product...")
            
            response = self.session.post(
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
                
                if "Manual Order / API platform" in response.text:
                    logger.info("💡 This is expected for Shopify stores - products sync through Shopify")
                    return {'sync_product': {'id': 'shopify-sync-pending'}}
                
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating product: {e}")
            return None
    
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
        
        # Prepare image for Printful
        logger.info("🖼️ Preparing image for Printful...")
        prepared_image = self.prepare_image_for_printful(design['image_data'])
        
        # Save locally (will be pushed to GitHub by the workflow)
        filename = self.save_design_locally(prepared_image, title, collection_key)
        if not filename:
            logger.error("❌ Failed to save design locally")
            return
        
        # Get GitHub URL (using raw URL for immediate access)
        github_url = self.get_github_url(filename)
        logger.info(f"🌐 GitHub URL: {github_url}")
        
        # Note about GitHub Actions
        if os.environ.get('GITHUB_ACTIONS'):
            logger.info("📝 Running in GitHub Actions - file will be pushed by workflow")
            logger.info("💡 Using raw.githubusercontent.com for immediate access")
        
        # Upload to Printful
        file_id = self.upload_to_printful(github_url, filename)
        
        if file_id:
            # Create product
            logger.info("🛍️ Creating Printful product...")
            product = self.create_printful_product(title, file_id, collection)
            
            if product:
                logger.info(f"✅ Successfully processed {collection_key}")
                logger.info(f"🎨 Title: {title}")
                logger.info(f"🆔 Product ID: {product['sync_product']['id']}")
        else:
            logger.warning("⚠️  Printful upload failed - this might be a timing issue")
            logger.info("💡 The file will be available after GitHub pushes it")
            logger.info(f"💡 Manual upload URL: {github_url}")
    
    def run_daily_generation(self):
        """Run the daily generation process."""
        logger.info("\n" + "="*50)
        logger.info("🚀 Starting Daily T-Shirt Generation")
        logger.info(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*50)
        
        # Log configuration
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
        logger.info("💡 Note: Using raw GitHub URLs for immediate access")
        logger.info("="*50)

def main():
    """Main entry point."""
    try:
        if os.environ.get('GITHUB_ACTIONS'):
            logger.info("📍 Running in: GitHub Actions")
        else:
            logger.info("📍 Running in: Local environment")
        
        logger.info(f"🐍 Python version: {sys.version}")
        
        generator = TShirtGenerator()
        generator.run_daily_generation()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        logger.error("Traceback:", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
