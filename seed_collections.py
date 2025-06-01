#!/usr/bin/env python3
"""
One-time setup script to create SMART collections in Shopify.
Creates collections.json mapping for use by other scripts.
"""

import os
import json
import logging
import requests
import urllib3
from typing import Dict
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

def create_shopify_collection(store: str, access_token: str, title: str, 
                            handle: str, rules: list) -> Dict:
    """Create a smart collection in Shopify with SSL handling."""
    headers = {
        'X-Shopify-Access-Token': access_token,
        'Content-Type': 'application/json'
    }
    
    collection_data = {
        'smart_collection': {
            'title': title,
            'handle': handle,
            'rules': rules,
            'published': True,
            'sort_order': 'best-selling'
        }
    }
    
    try:
        response = requests.post(
            f'https://{store}.myshopify.com/admin/api/2024-04/smart_collections.json',
            headers=headers,
            json=collection_data,
            timeout=30,
            verify=False  # Disable SSL verification for GitHub Actions
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error creating collection '{title}': {e}")
        raise

def main():
    """Create all required collections."""
    # Get environment variables
    store = os.getenv('SHOPIFY_STORE')
    access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
    
    if not store or not access_token:
        raise ValueError("Missing SHOPIFY_STORE or SHOPIFY_ACCESS_TOKEN environment variables")
    
    logger.info("Starting collection seeding process...")
    
    # Define collections to create
    collections_config = [
        {
            'key': 'brit-pride',
            'title': 'Proper British',
            'handle': 'proper-british',
            'theme': 'British pride t-shirt design, Union Jack elements, tea culture, queue jokes, weather humor',
            'rules': [
                {
                    'column': 'tag',
                    'relation': 'equals',
                    'condition': 'british-pride'
                }
            ]
        },
        {
            'key': 'brit-humour',
            'title': 'British Banter',
            'handle': 'british-banter',
            'theme': 'British sarcasm t-shirt design, dry wit, taking the piss, understatement humor',
            'rules': [
                {
                    'column': 'tag',
                    'relation': 'equals',
                    'condition': 'british-humour'
                }
            ]
        },
        {
            'key': 'pub-culture',
            'title': 'Pub Life',
            'handle': 'pub-life',
            'theme': 'British pub culture t-shirt design, beer, Sunday roast, fancy a pint, local pub vibes',
            'rules': [
                {
                    'column': 'tag',
                    'relation': 'equals',
                    'condition': 'pub-culture'
                }
            ]
        },
        {
            'key': 'football-mad',
            'title': 'Football Mad',
            'handle': 'football-mad',
            'theme': 'British football culture t-shirt design, coming home jokes, penalty shootouts, VAR complaints',
            'rules': [
                {
                    'column': 'tag',
                    'relation': 'equals',
                    'condition': 'football-mad'
                }
            ]
        },
        {
            'key': 'tea-time',
            'title': 'Tea Time',
            'handle': 'tea-time',
            'theme': 'British tea culture t-shirt design, proper brew, biscuits, milk first debate, cuppa jokes',
            'rules': [
                {
                    'column': 'tag',
                    'relation': 'equals',
                    'condition': 'tea-time'
                }
            ]
        },
        {
            'key': 'weather-talk',
            'title': 'Weather Talk',
            'handle': 'weather-talk',
            'theme': 'British weather obsession t-shirt design, rain jokes, sunshine panic, small talk culture',
            'rules': [
                {
                    'column': 'tag',
                    'relation': 'equals',
                    'condition': 'weather-talk'
                }
            ]
        }
    ]
    
    # Create collections and build mapping
    collections_mapping = {}
    
    for config in collections_config:
        try:
            logger.info(f"Creating collection: {config['title']}")
            result = create_shopify_collection(
                store, 
                access_token, 
                config['title'], 
                config['handle'], 
                config['rules']
            )
            
            collection_id = result['smart_collection']['id']
            
            collections_mapping[config['key']] = {
                'shopify_id': str(collection_id),
                'title': config['title'],
                'handle': config['handle'],
                'theme': config['theme']
            }
            
            logger.info(f"✅ Created '{config['title']}' with ID: {collection_id}")
            
        except Exception as e:
            logger.error(f"Failed to create collection '{config['title']}': {e}")
            continue
    
    # Save mapping to JSON file
    if collections_mapping:
        with open('collections.json', 'w') as f:
            json.dump(collections_mapping, f, indent=2)
        
        logger.info(f"✅ Successfully created {len(collections_mapping)} collections")
        logger.info("Collections mapping saved to collections.json")
        
        # Print summary
        for key, collection in collections_mapping.items():
            logger.info(f"  {key}: {collection['title']} (ID: {collection['shopify_id']})")
    else:
        logger.error("❌ No collections were created successfully")
        raise Exception("Failed to create any collections")

if __name__ == "__main__":
    main()
