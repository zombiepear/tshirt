#!/usr/bin/env python3
"""
Bulk T-Shirt Design Generator
Generates multiple t-shirt designs with configurable parameters
"""

import argparse
import time
import json
from datetime import datetime
from generate_tee import generate_design, upload_to_printful, create_shopify_product, DESIGN_CATEGORIES

def bulk_generate(category=None, count=1, delay=5):
    """Generate multiple designs with delay between each"""
    
    print(f"=== Bulk T-Shirt Design Generation ===")
    print(f"Category: {category or 'Random'}")
    print(f"Count: {count}")
    print(f"Delay: {delay} seconds")
    print("=" * 40)
    
    results = []
    successful = 0
    failed = 0
    
    for i in range(count):
        print(f"\nGenerating design {i + 1} of {count}...")
        
        try:
            # Generate design
            design = generate_design(category)
            
            if design:
                # Upload to Printful
                printful_id = upload_to_printful(design)
                
                # Create Shopify product
                shopify_id = create_shopify_product(design, printful_id)
                
                # Record result
                result = {
                    "index": i + 1,
                    "timestamp": datetime.now().isoformat(),
                    "status": "success",
                    "design": {
                        "filename": design["filename"],
                        "category": design["category"],
                        "theme": design["theme"]
                    },
                    "printful_product_id": printful_id,
                    "shopify_product_id": shopify_id
                }
                
                results.append(result)
                successful += 1
                print(f"✓ Design {i + 1} generated successfully!")
                
            else:
                results.append({
                    "index": i + 1,
                    "timestamp": datetime.now().isoformat(),
                    "status": "failed",
                    "error": "Design generation failed"
                })
                failed += 1
                print(f"✗ Design {i + 1} failed to generate")
                
        except Exception as e:
            results.append({
                "index": i + 1,
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            })
            failed += 1
            print(f"✗ Design {i + 1} error: {str(e)}")
        
        # Delay between generations (except for the last one)
        if i < count - 1:
            print(f"Waiting {delay} seconds before next generation...")
            time.sleep(delay)
    
    # Summary
    print("\n" + "=" * 40)
    print(f"BULK GENERATION COMPLETE")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total: {count}")
    print("=" * 40)
    
    # Save bulk results
    bulk_log = {
        "session": {
            "start_time": results[0]["timestamp"] if results else datetime.now().isoformat(),
            "end_time": datetime.now().isoformat(),
            "category": category or "random",
            "requested_count": count,
            "successful_count": successful,
            "failed_count": failed
        },
        "results": results
    }
    
    filename = f"bulk_generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(bulk_log, f, indent=2)
    
    print(f"\nBulk generation log saved to: {filename}")
    
    # Also append to main generation log
    log_filename = "generation_log.json"
    logs = []
    
    try:
        with open(log_filename, 'r') as f:
            logs = json.load(f)
    except:
        pass
    
    # Add successful designs to main log
    for result in results:
        if result["status"] == "success":
            logs.append({
                "timestamp": result["timestamp"],
                "design": result["design"],
                "printful_product_id": result.get("printful_product_id"),
                "shopify_product_id": result.get("shopify_product_id"),
                "bulk_session": filename
            })
    
    with open(log_filename, 'w') as f:
        json.dump(logs, f, indent=2)
    
    return results

def main():
    """Main function with argument parsing"""
    
    parser = argparse.ArgumentParser(description='Bulk generate t-shirt designs')
    parser.add_argument(
        '--category', 
        type=str, 
        default=None,
        choices=[''] + list(DESIGN_CATEGORIES.keys()),
        help='Design category (leave empty for random)'
    )
    parser.add_argument(
        '--count', 
        type=int, 
        default=1,
        help='Number of designs to generate (default: 1)'
    )
    parser.add_argument(
        '--delay', 
        type=int, 
        default=5,
        help='Delay in seconds between generations (default: 5)'
    )
    
    args = parser.parse_args()
    
    # Handle empty string category
    category = args.category if args.category else None
    
    # Run bulk generation
    bulk_generate(
        category=category,
        count=args.count,
        delay=args.delay
    )

if __name__ == "__main__":
    main()
