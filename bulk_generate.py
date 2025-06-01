#!/usr/bin/env python3
"""
Bulk T-shirt generation CLI for back-filling catalogue.
Usage: python bulk_generate.py --count 10 --categories retro,local,politics
"""

import argparse
import sys
import time
from generate_tee import TShirtGenerator
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Bulk generate T-shirt designs for catalogue back-filling'
    )
    
    parser.add_argument(
        '--count', '-c',
        type=int,
        required=True,
        help='Number of designs to generate per category'
    )
    
    parser.add_argument(
        '--categories', '-cat',
        type=str,
        help='Comma-separated list of categories (default: all)',
        default=None
    )
    
    parser.add_argument(
        '--delay', '-d',
        type=int,
        default=5,
        help='Delay between generations in seconds (default: 5)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be generated without actually creating products'
    )
    
    return parser.parse_args()

def validate_categories(categories_str: str, available_categories: list) -> list:
    """Validate and return list of categories."""
    if not categories_str:
        return available_categories
    
    categories = [cat.strip() for cat in categories_str.split(',')]
    invalid_categories = [cat for cat in categories if cat not in available_categories]
    
    if invalid_categories:
        logger.error(f"Invalid categories: {', '.join(invalid_categories)}")
        logger.info(f"Available categories: {', '.join(available_categories)}")
        sys.exit(1)
    
    return categories

def main():
    """Main execution function."""
    args = parse_arguments()
    
    try:
        generator = TShirtGenerator()
        available_categories = list(generator.collections.keys())
        
        # Validate categories
        target_categories = validate_categories(args.categories, available_categories)
        
        total_designs = len(target_categories) * args.count
        
        print("\n" + "="*60)
        print("BULK T-SHIRT GENERATION")
        print("="*60)
        print(f"Categories: {', '.join(target_categories)}")
        print(f"Designs per category: {args.count}")
        print(f"Total designs: {total_designs}")
        print(f"Delay between generations: {args.delay}s")
        print(f"Dry run: {args.dry_run}")
        print("="*60)
        
        if args.dry_run:
            print("\nDRY RUN - No actual products will be created")
            for i in range(args.count):
                for category in target_categories:
                    collection_name = generator.collections[category]['name']
                    print(f"Would generate: {collection_name} Design #{i+1}")
            print(f"\nTotal: {total_designs} designs would be created")
            return
        
        # Confirm before proceeding
        confirm = input(f"\nProceed with generating {total_designs} designs? (y/N): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            return
        
        print("\nStarting bulk generation...\n")
        
        generated_count = 0
        failed_count = 0
        
        for i in range(args.count):
            for category in target_categories:
                try:
                    logger.info(f"Generating design {i+1}/{args.count} for {category}")
                    generator.generate_daily_designs([category])
                    generated_count += 1
                    
                    # Delay between generations to respect rate limits
                    if generated_count < total_designs:
                        time.sleep(args.delay)
                        
                except Exception as e:
                    logger.error(f"Failed to generate design for {category}: {e}")
                    failed_count += 1
        
        print("\n" + "="*60)
        print("BULK GENERATION COMPLETE")
        print("="*60)
        print(f"Successfully generated: {generated_count}")
        print(f"Failed: {failed_count}")
        print(f"Total attempted: {total_designs}")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\nGeneration interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Bulk generation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
config.example.env
env# OpenAI API Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here

# Shopify Store Configuration
SHOPIFY_STORE=your-store-name
SHOPIFY_ACCESS_TOKEN=shpat_your-access-token-here

# Printful API Configuration
PRINTFUL_API_KEY=your-printful-api-key-here

# Pricing Configuration
MARKUP_PERCENT=1.4

# Optional: Logging Level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
