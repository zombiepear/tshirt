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
    
    # Define collections to create - including celebrations, events, and occasions
    collections_config = [
        # Celebrations & Events
        {
            'key': 'birthday-party',
            'title': 'Birthday Celebrations',
            'handle': 'birthday-celebrations',
            'theme': 'Birthday party t-shirt design, cake, balloons, party hats, funny age jokes, birthday wishes'
        },
        {
            'key': 'christmas-festive',
            'title': 'Christmas & Holiday',
            'handle': 'christmas-holiday',
            'theme': 'Christmas holiday t-shirt design, Santa, reindeer, snow, festive vibes, holiday cheer'
        },
        {
            'key': 'wedding-love',
            'title': 'Weddings & Love',
            'handle': 'weddings-love',
            'theme': 'Wedding celebration t-shirt design, bride, groom, love hearts, romance, marriage humor'
        },
        {
            'key': 'stag-party',
            'title': 'Stag Party',
            'handle': 'stag-party',
            'theme': 'Stag do t-shirt design, bachelor party, lads night out, drinking games, last night of freedom'
        },
        {
            'key': 'hen-party',
            'title': 'Hen Party',
            'handle': 'hen-party',
            'theme': 'Hen do t-shirt design, bachelorette party, girls night out, bride tribe, fun celebrations'
        },
        {
            'key': 'christening-baby',
            'title': 'Christenings & Babies',
            'handle': 'christenings-babies',
            'theme': 'Christening ceremony t-shirt design, baby celebration, baptism, new life, family gathering'
        },
        {
            'key': 'anniversary-milestone',
            'title': 'Anniversaries',
            'handle': 'anniversaries',
            'theme': 'Anniversary celebration t-shirt design, milestone years, love endures, relationship goals'
        },
        {
            'key': 'graduation-achievement',
            'title': 'Graduation & Success',
            'handle': 'graduation-success',
            'theme': 'Graduation achievement t-shirt design, cap and gown, diploma, academic success, future goals'
        },
        {
            'key': 'retirement-freedom',
            'title': 'Retirement Party',
            'handle': 'retirement-party',
            'theme': 'Retirement celebration t-shirt design, freedom at last, no more Mondays, pension life'
        },
        {
            'key': 'new-year-fresh',
            'title': 'New Year Fresh Start',
            'handle': 'new-year-fresh',
            'theme': 'New Year resolution t-shirt design, fresh start, midnight countdown, champagne celebration'
        },
        # British Humor (keeping a few)
        {
            'key': 'brit-pride',
            'title': 'Proper British',
            'handle': 'proper-british',
            'theme': 'British pride t-shirt design, Union Jack elements, tea culture, queue jokes, weather humor'
        },
        {
            'key': 'pub-culture',
            'title': 'Pub Life',
            'handle': 'pub-life',
            'theme': 'British pub culture t-shirt design, beer, Sunday roast, fancy a pint, local pub vibes'
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
