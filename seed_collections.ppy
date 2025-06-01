#!/usr/bin/env python3
"""
One-time setup script to create SMART collections in Shopify.
Creates collections.json mapping for use by other scripts.
"""

import os
import json
import requests
import logging
from typing import Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CollectionSeeder:
    def __init__(self):
        """Initialize Shopify API client."""
        self.shopify_store = os.getenv('SHOPIFY_STORE')
        self.shopify_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        
        if not self.shopify_store or not self.shopify_token:
            raise ValueError("Missing SHOPIFY_STORE or SHOPIFY_ACCESS_TOKEN")
        
        self.shopify_base = f"https://{self.shopify_store}.myshopify.com/admin/api/2024-04"
        
        # Collection definitions
        self.collections = {
            'brit-pride': {
                'name': 'Proper British',
                'description': "Celebrate British culture, tea obsession, and everything that makes us brilliantly British",
                'tag': 'brit-pride'
            },
            'brit-humour': {
                'name': 'British Banter',
                'description': "Dry wit, sarcasm, and the art of taking the piss - British humor at its finest",
                'tag': 'brit-humour'
            },
            'pub-culture': {
                'name': 'Pub Life',
                'description': "Sunday roasts, proper pints, and the heart of British social life",
                'tag': 'pub-culture'
            },
            'tea-obsessed': {
                'name': 'Tea & Biscuits',
                'description': "For those who know a proper brew solves everything",
                'tag': 'tea-obsessed'
            },
            'regional-pride': {
                'name': 'Local Heroes',
                'description': "Celebrate your corner of Britain - from Manchester to Edinburgh and everywhere between",
                'tag': 'regional-pride'
            },
            'christmas': {
                'name': 'Christmas Crackers',
                'description': "British Christmas traditions, festive jumpers, and Boxing Day vibes",
                'tag': 'christmas'
            },
            'easter': {
                'name': 'Easter Treats',
                'description': "Spring celebrations, chocolate eggs, and bank holiday mood",
                'tag': 'easter'
            },
            'seasons': {
                'name': 'Seasonal Vibes',
                'description': "Four seasons in one day? That's just Tuesday in Britain",
                'tag': 'seasons'
            },
            'bonfire-night': {
                'name': 'Remember Remember',
                'description': "Guy Fawkes, fireworks, and uniquely British autumn traditions",
                'tag': 'bonfire-night'
            },
            'birthdays': {
                'name': 'Birthday Legends',
                'description': "Celebrate another year of being absolutely brilliant",
                'tag': 'birthdays'
            },
            'celebrations': {
                'name': 'Life Moments',
                'description': "Graduations, achievements, and all those milestone moments worth celebrating",
                'tag': 'celebrations'
            },
            'motivation': {
                'name': 'Daily Grind',
                'description': "Monday motivation and the mindset to tackle whatever life throws at you",
                'tag': 'motivation'
            },
            'pet-parents': {
                'name': 'Fur Baby Love',
                'description': "For those whose pets are family - dog walks, cat cuddles, and unconditional love",
                'tag': 'pet-parents'
            },
            'geek-culture': {
                'name': 'Proper Nerdy',
                'description': "Gaming, sci-fi, tech humor - where being a geek is absolutely brilliant",
                'tag': 'geek-culture'
            },
            'food-obsessed': {
                'name': 'Foodie Life',
                'description': "Full English breakfasts, Sunday roasts, and a proper appreciation for good food",
                'tag': 'food-obsessed'
            }
        }

    def create_smart_collection(self, slug: str, collection_data: Dict) -> str:
        """Create a SMART collection in Shopify."""
        headers = {
            'X-Shopify-Access-Token': self.shopify_token,
            'Content-Type': 'application/json'
        }
        
        # Create SMART collection with tag-based rules
        payload = {
            'smart_collection': {
                'title': collection_data['name'],
                'body_html': f"<p>{collection_data['description']}</p>",
                'sort_order': 'created-desc',
                'rules': [{
                    'column': 'tag',
                    'relation': 'equals',
                    'condition': collection_data['tag']
                }],
                'published': True
            }
        }
        
        try:
            response = requests.post(
                f"{self.shopify_base}/smart_collections.json",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 201:
                collection_id = response.json()['smart_collection']['id']
                logger.info(f"Created collection '{collection_data['name']}' with ID: {collection_id}")
                return str(collection_id)
            else:
                logger.error(f"Failed to create collection '{collection_data['name']}': {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating collection '{collection_data['name']}': {e}")
            return None

    def seed_all_collections(self):
        """Create all collections and save mapping to JSON."""
        collections_map = {}
        
        logger.info("Starting collection seeding process...")
        
        for slug, collection_data in self.collections.items():
            collection_id = self.create_smart_collection(slug, collection_data)
            if collection_id:
                collections_map[slug] = collection_id
        
        # Save collections mapping to JSON file
        try:
            with open('collections.json', 'w') as f:
                json.dump(collections_map, f, indent=2)
            logger.info(f"Collections mapping saved to collections.json")
            logger.info(f"Successfully created {len(collections_map)} collections")
        except Exception as e:
            logger.error(f"Failed to save collections mapping: {e}")
        
        return collections_map

def main():
    """Main execution function."""
    try:
        seeder = CollectionSeeder()
        collections_map = seeder.seed_all_collections()
        
        print("\n" + "="*50)
        print("COLLECTION SEEDING COMPLETE")
        print("="*50)
        for slug, collection_id in collections_map.items():
            print(f"{slug:<15} → {collection_id}")
        print("="*50)
        print("Collections mapping saved to collections.json")
        print("You can now run generate_tee.py or bulk_generate.py")
        
    except Exception as e:
        logger.error(f"Collection seeding failed: {e}")
        raise

if __name__ == "__main__":
    main()
