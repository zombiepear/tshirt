#!/usr/bin/env python3
"""
Daily T-shirt design generator and Shopify/Printful automation.
Runs daily at 08:00 UK time to create new designs for each collection.
"""

import os
import json
import time
import requests
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

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
        """Initialize API clients and configuration."""
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.shopify_store = os.getenv('SHOPIFY_STORE')
        self.shopify_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        self.printful_key = os.getenv('PRINTFUL_API_KEY')
        self.markup_percent = float(os.getenv('MARKUP_PERCENT', '1.4'))
        
        # Validate required environment variables
        required_vars = ['OPENAI_API_KEY', 'SHOPIFY_STORE', 'SHOPIFY_ACCESS_TOKEN', 'PRINTFUL_API_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # API endpoints
        self.shopify_base = f"https://{self.shopify_store}.myshopify.com/admin/api/2024-04"
        self.printful_base = "https://api.printful.com"
        
        # Collection definitions with prompts
        self.collections = {
            'brit-pride': {
                'name': 'Proper British',
                'prompt': "British pride t-shirt design, Union Jack elements, tea culture, queue jokes, weather humor"
            },
            'brit-humour': {
                'name': 'British Banter',
                'prompt': "British sarcasm t-shirt design, dry wit, taking the piss, understatement humor"
            },
            'pub-culture': {
                'name': 'Pub Life',
                'prompt': "British pub culture t-shirt design, beer, Sunday roast, fancy a pint, local pub vibes"
            },
            'tea-obsessed': {
                'name': 'Tea & Biscuits',
                'prompt': "British tea obsession t-shirt design, proper brew, digestives, put the kettle on"
            },
            'regional-pride': {
                'name': 'Local Heroes',
                'prompt': "British regional pride t-shirt design, Manchester Liverpool Birmingham Scottish Welsh Yorkshire"
            },
            'christmas': {
                'name': 'Christmas Crackers',
                'prompt': "British Christmas t-shirt design, Christmas jumper, Boxing Day, festive traditions"
            },
            'easter': {
                'name': 'Easter Treats',
                'prompt': "Easter t-shirt design, chocolate eggs, spring vibes, British bank holiday mood"
            },
            'seasons': {
                'name': 'Seasonal Vibes',
                'prompt': "British seasons t-shirt design, weather jokes, four seasons in one day, seasonal humor"
            },
            'bonfire-night': {
                'name': 'Remember Remember',
                'prompt': "Guy Fawkes bonfire night t-shirt design, fireworks, British autumn traditions"
            },
            'birthdays': {
                'name': 'Birthday Legends',
                'prompt': "birthday celebration t-shirt design, age jokes, birthday month pride, celebration vibes"
            },
            'celebrations': {
                'name': 'Life Moments',
                'prompt': "celebration t-shirt design, graduations, achievements, milestones, life moments"
            },
            'motivation': {
                'name': 'Daily Grind',
                'prompt': "motivational t-shirt design, Monday motivation, hustle culture, you've got this"
            },
            'pet-parents': {
                'name': 'Fur Baby Love',
                'prompt': "pet parent t-shirt design, dog walking, cat obsession, fur baby love, pet humor"
            },
            'geek-culture': {
                'name': 'Proper Nerdy',
                'prompt': "geek culture t-shirt design, gaming, sci-fi, tech jokes, nerd pride"
            },
            'food-obsessed': {
                'name': 'Foodie Life',
                'prompt': "British food t-shirt design, full English, fish and chips, Sunday roast, foodie love"
            }
        }

    def retry_request(self, func, max_retries: int = 3, delay: float = 1.0) -> requests.Response:
        """Retry HTTP requests with exponential backoff."""
        for attempt in range(max_retries):
            try:
                response = func()
                if response.status_code == 429:  # Rate limited
                    wait_time = delay * (2 ** attempt)
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                return response
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    raise e
                wait_time = delay * (2 ** attempt)
                logger.warning(f"Request failed. Retrying in {wait_time}s. Error: {e}")
                time.sleep(wait_time)
        
        raise Exception("Max retries exceeded")

    def generate_design(self, prompt: str, category: str) -> Optional[str]:
        """Generate T-shirt design using OpenAI DALL-E API."""
        logger.info(f"Generating design for {category}: {prompt}")
        
        headers = {
            'Authorization': f'Bearer {self.openai_api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'dall-e-3',
            'prompt': f"{prompt}, transparent background, t-shirt design, high quality, 1024x1024",
            'size': '1024x1024',
            'quality': 'standard',
            'n': 1,
            'response_format': 'url'
        }
        
        def make_request():
            return requests.post(
                'https://api.openai.com/v1/images/generations',
                headers=headers,
                json=payload
            )
        
        try:
            response = self.retry_request(make_request)
            if response.status_code == 200:
                data = response.json()
                image_url = data['data'][0]['url']
                logger.info(f"Design generated successfully for {category}")
                return image_url
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Failed to generate design for {category}: {e}")
            return None

    def upload_to_printful(self, image_url: str, title: str) -> Optional[Tuple[str, float]]:
        """Upload design to Printful and create product."""
        logger.info(f"Uploading to Printful: {title}")
        
        headers = {
            'Authorization': f'Bearer {self.printful_key}',
            'Content-Type': 'application/json'
        }
        
        # First, upload the design file
        file_payload = {
            'url': image_url,
            'filename': f"{title.replace(' ', '_')}.png"
        }
        
        def upload_file():
            return requests.post(
                f"{self.printful_base}/files",
                headers=headers,
                json=file_payload
            )
        
        try:
            file_response = self.retry_request(upload_file)
            if file_response.status_code != 200:
                logger.error(f"Failed to upload file to Printful: {file_response.text}")
                return None
            
            file_data = file_response.json()
            file_id = file_data['result']['id']
            
            # Create product with Bella Canvas 3001
            product_payload = {
                'sync_product': {
                    'name': title,
                    'thumbnail': image_url
                },
                'sync_variants': [{
                    'retail_price': '0.00',  # Will be calculated after getting cost
                    'variant_id': 4011,  # Bella Canvas 3001 - S
                    'files': [{
                        'id': file_id,
                        'type': 'front',
                        'position': {
                            'area_width': 1800,
                            'area_height': 2400,
                            'width': 1800,
                            'height': 1800,
                            'top': 300,
                            'left': 0
                        }
                    }]
                }]
            }
            
            def create_product():
                return requests.post(
                    f"{self.printful_base}/store/products",
                    headers=headers,
                    json=product_payload
                )
            
            product_response = self.retry_request(create_product)
            if product_response.status_code == 200:
                product_data = product_response.json()
                product_id = product_data['result']['id']
                
                # Get pricing information
                def get_pricing():
                    return requests.get(
                        f"{self.printful_base}/store/products/{product_id}",
                        headers=headers
                    )
                
                pricing_response = self.retry_request(get_pricing)
                if pricing_response.status_code == 200:
                    pricing_data = pricing_response.json()
                    base_cost = float(pricing_data['result']['sync_variants'][0]['costs']['total'])
                    retail_price = round(base_cost * self.markup_percent, 2)
                    
                    # Update with calculated price
                    update_payload = {
                        'sync_variants': [{
                            'id': pricing_data['result']['sync_variants'][0]['id'],
                            'retail_price': f"{retail_price:.2f}"
                        }]
                    }
                    
                    def update_pricing():
                        return requests.put(
                            f"{self.printful_base}/store/products/{product_id}",
                            headers=headers,
                            json=update_payload
                        )
                    
                    self.retry_request(update_pricing)
                    logger.info(f"Printful product created: {product_id} at £{retail_price}")
                    return product_id, retail_price
                    
            logger.error(f"Failed to create Printful product: {product_response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Printful upload failed for {title}: {e}")
            return None

    def create_shopify_product(self, title: str, price: float, category: str, printful_id: str) -> Optional[str]:
        """Create product in Shopify and assign to collections."""
        logger.info(f"Creating Shopify product: {title}")
        
        today = datetime.now().strftime('%Y-%m-%d')
        tags = [category, 'tshirt-uk', 'daily-design', today]
        
        headers = {
            'X-Shopify-Access-Token': self.shopify_token,
            'Content-Type': 'application/json'
        }
        
        product_payload = {
            'product': {
                'title': title,
                'body_html': f"<p>Fresh daily design from our {self.collections[category]['name']} collection.</p>",
                'vendor': 'tshirt.uk',
                'product_type': 'T-Shirt',
                'tags': ', '.join(tags),
                'status': 'active',
                'variants': [{
                    'price': f"{price:.2f}",
                    'inventory_management': 'printful',
                    'fulfillment_service': 'printful'
                }]
            }
        }
        
        def create_product():
            return requests.post(
                f"{self.shopify_base}/products.json",
                headers=headers,
                json=product_payload
            )
        
        try:
            response = self.retry_request(create_product)
            if response.status_code == 201:
                product_data = response.json()
                product_id = product_data['product']['id']
                
                # Assign to collections
                self.assign_to_collections(product_id, category, headers)
                
                logger.info(f"Shopify product created: {product_id}")
                return str(product_id)
            else:
                logger.error(f"Failed to create Shopify product: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Shopify product creation failed for {title}: {e}")
            return None

    def assign_to_collections(self, product_id: str, category: str, headers: Dict):
        """Assign product to relevant collections."""
        try:
            # Load collections mapping
            if os.path.exists('collections.json'):
                with open('collections.json', 'r') as f:
                    collections_map = json.load(f)
                
                collections_to_assign = [category]
                
                for collection_slug in collections_to_assign:
                    if collection_slug in collections_map:
                        collection_id = collections_map[collection_slug]
                        
                        collect_payload = {
                            'collect': {
                                'product_id': product_id,
                                'collection_id': collection_id
                            }
                        }
                        
                        def add_to_collection():
                            return requests.post(
                                f"{self.shopify_base}/collects.json",
                                headers=headers,
                                json=collect_payload
                            )
                        
                        self.retry_request(add_to_collection)
                        logger.info(f"Added product {product_id} to collection {collection_slug}")
        except Exception as e:
            logger.error(f"Failed to assign collections: {e}")

    def generate_daily_designs(self, categories: Optional[List[str]] = None):
        """Generate designs for all collections or specified categories."""
        target_categories = categories or list(self.collections.keys())
        
        for category in target_categories:
            if category not in self.collections:
                logger.warning(f"Unknown category: {category}")
                continue
                
            collection_info = self.collections[category]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            title = f"{collection_info['name']} Design {timestamp}"
            
            # Generate design
            image_url = self.generate_design(collection_info['prompt'], category)
            if not image_url:
                continue
            
            # Upload to Printful
            printful_result = self.upload_to_printful(image_url, title)
            if not printful_result:
                continue
                
            printful_id, price = printful_result
            
            # Create Shopify product
            shopify_id = self.create_shopify_product(title, price, category, printful_id)
            if shopify_id:
                logger.info(f"✅ {title} | {category} | £{price} | {shopify_id}")
            
            # Small delay between products to avoid rate limits
            time.sleep(2)

def main():
    """Main execution function."""
    try:
        generator = TShirtGenerator()
        generator.generate_daily_designs()
        logger.info("Daily design generation completed successfully")
    except Exception as e:
        logger.error(f"Daily generation failed: {e}")
        raise

if __name__ == "__main__":
    main()
