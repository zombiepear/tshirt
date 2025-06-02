#!/usr/bin/env python3
"""
Bulk T-shirt generation for GitHub Actions
Usage: python bulk_generate.py --count 10 --categories gaming,coffee,fitness
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
        description='Bulk generate T-shirt designs'
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
    
    return parser.parse_args()

def main():
    """Main execution function."""
    args = parse_arguments()
    
    try:
        generator = TShirtGenerator()
        available_categories = list(generator.collections.keys())
        
        # Determine which categories to use
        if args.categories:
            categories = [cat.strip() for cat in args.categories.split(',')]
            # Validate categories
            invalid = [cat for cat in categories if cat not in available_categories]
            if invalid:
                logger.error(f"❌ Invalid categories: {', '.join(invalid)}")
                logger.info(f"Available: {', '.join(available_categories)}")
                sys.exit(1)
        else:
            categories = available_categories
        
        total_designs = len(categories) * args.count
        
        logger.info("="*60)
        logger.info("BULK T-SHIRT GENERATION")
        logger.info("="*60)
        logger.info(f"Categories: {', '.join(categories)}")
        logger.info(f"Designs per category: {args.count}")
        logger.info(f"Total designs: {total_designs}")
        logger.info(f"Delay between generations: {args.delay}s")
        logger.info("="*60)
        
        generated_count = 0
        failed_count = 0
        
        for i in range(args.count):
            for category in categories:
                try:
                    logger.info(f"\n📦 Generating design {i+1}/{args.count} for {category}")
                    generator.generate_daily_designs([category])
                    generated_count += 1
                    
                    # Delay between generations to respect rate limits
                    if generated_count < total_designs:
                        logger.info(f"⏳ Waiting {args.delay} seconds...")
                        time.sleep(args.delay)
                        
                except Exception as e:
                    logger.error(f"❌ Failed to generate design for {category}: {e}")
                    failed_count += 1
        
        logger.info("\n" + "="*60)
        logger.info("BULK GENERATION COMPLETE")
        logger.info("="*60)
        logger.info(f"✅ Successfully generated: {generated_count}")
        logger.info(f"❌ Failed: {failed_count}")
        logger.info(f"📊 Total attempted: {total_designs}")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"❌ Bulk generation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
