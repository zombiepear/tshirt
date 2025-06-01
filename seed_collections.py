#!/usr/bin/env python3
"""
One-time setup script to create collections mapping WITHOUT actually creating Shopify collections.
Creates collections.json mapping for use by other scripts.
"""

import os
import json
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Create collections mapping without actually creating Shopify collections."""
    logger.info("Starting collection mapping process (no Shopify collections created)...")
    
    # Define collections themes (we'll skip creating actual Shopify collections)
    collections_config = [
        {
            'key': 'brit-pride',
            'title': 'Proper British',
            'handle': 'proper-british',
            'theme': 'British pride t-shirt design, Union Jack elements, tea culture, queue jokes, weather humor'
        },
        {
            'key': 'brit-humour',
            'title': 'British Banter',
            'handle': 'british-banter',
            'theme': 'British sarcasm t-shirt design, dry wit, taking the piss, understatement humor'
        },
        {
            'key': 'pub-culture',
            'title': 'Pub Life',
            'handle': 'pub-life',
            'theme': 'British pub culture t-shirt design, beer, Sunday roast, fancy a pint, local pub vibes'
        },
        {
            'key': 'football-mad',
            'title': 'Football Mad',
            'handle': 'football-mad',
            'theme': 'British football culture t-shirt design, coming home jokes, penalty shootouts, VAR complaints'
        },
        {
            'key': 'tea-time',
            'title': 'Tea Time',
            'handle': 'tea-time',
            'theme': 'British tea culture t-shirt design, proper brew, biscuits, milk first debate, cuppa jokes'
        },
        {
            'key': 'weather-talk',
            'title': 'Weather Talk',
            'handle': 'weather-talk',
            'theme': 'British weather obsession t-shirt design, rain jokes, sunshine panic, small talk culture'
        }
    ]
    
    # Create collections mapping (without actual Shopify collections)
    collections_mapping = {}
    
    for config in collections_config:
        collections_mapping[config['key']] = {
            'shopify_id': None,  # No collection ID since we're not creating them
            'title': config['title'],
            'handle': config['handle'],
            'theme': config['theme']
        }
        logger.info(f"✅ Added mapping for '{config['title']}'")
    
    # Save mapping to JSON file
    with open('collections.json', 'w') as f:
        json.dump(collections_mapping, f, indent=2)
    
    logger.info(f"✅ Successfully created {len(collections_mapping)} collection mappings")
    logger.info("Collections mapping saved to collections.json")
    logger.info("NOTE: No actual Shopify collections were created - products will be ungrouped")
    
    # Print summary
    for key, collection in collections_mapping.items():
        logger.info(f"  {key}: {collection['title']}")

if __name__ == "__main__":
    main()
