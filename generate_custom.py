#!/usr/bin/env python3
"""
Custom Prompt T-Shirt Design Generator
Allows generation of t-shirt designs with custom prompts
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime
from openai import OpenAI
from generate_tee import upload_to_printful, create_shopify_product

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def generate_custom_design(custom_prompt, style_hint=None):
    """Generate a t-shirt design from a custom prompt"""
    
    # Build the full prompt with t-shirt specifications
    full_prompt = f"""Create a SINGLE, professional t-shirt design based on this concept:

{custom_prompt}

CRITICAL REQUIREMENTS:
- Generate only ONE unified design - absolutely no multiple versions or comparisons
- Single, centered composition suitable for t-shirt printing
- Clean edges with transparent or white background
- Bold, eye-catching artwork that works well on fabric
- Professional quality suitable for commercial use
- No split screens, panels, or variations
- Design should fill the canvas appropriately for t-shirt printing
"""

    # Add style hint if provided
    if style_hint:
        full_prompt += f"\nStyle direction: {style_hint}"
    
    print("Generating custom design...")
    print(f"User prompt: {custom_prompt}")
    print(f"Style hint: {style_hint or 'None'}")
    
    try:
        # Generate image with DALL-E 3
        response = client.images.generate(
            model="dall-e-3",
            prompt=full_prompt,
            size="1024x1024",
            quality="standard",
            style="vivid",
            n=1
        )
        
        image_url = response.data[0].url
        revised_prompt = response.data[0].revised_prompt
        
        print("Design generated successfully!")
        print(f"Revised prompt: {revised_prompt[:200]}...")
        
        # Download the image
        image_response = requests.get(image_url)
        image_response.raise_for_status()
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Create safe filename from prompt (first 30 chars, alphanumeric only)
        safe_prompt = ''.join(c for c in custom_prompt[:30] if c.isalnum() or c in (' ', '-', '_'))
        safe_prompt = safe_prompt.replace(' ', '_')
        filename = f"design_custom_{safe_prompt}_{timestamp}.png"
        
        # Save the image
        with open(filename, 'wb') as f:
            f.write(image_response.content)
        
        print(f"Design saved as: {filename}")
        
        return {
            "filename": filename,
            "category": "custom",
            "theme": custom_prompt[:50] + "..." if len(custom_prompt) > 50 else custom_prompt,
            "prompt": full_prompt,
            "revised_prompt": revised_prompt,
            "image_url": image_url,
            "image_data": image_response.content,
            "custom_prompt": custom_prompt,
            "style_hint": style_hint
        }
        
    except Exception as e:
        print(f"Error generating design: {str(e)}")
        return None

def main():
    """Main function with argument parsing"""
    
    parser = argparse.ArgumentParser(
        description='Generate t-shirt designs from custom prompts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_custom.py "A majestic dragon breathing rainbow fire"
  python generate_custom.py "Retro 80s synthwave sunset" --style "vaporwave aesthetic"
  python generate_custom.py "Cats playing poker in space" --style "whimsical cartoon" --upload
        """
    )
    
    parser.add_argument(
        'prompt',
        type=str,
        help='Your custom design prompt'
    )
    
    parser.add_argument(
        '--style',
        type=str,
        default=None,
        help='Optional style hint (e.g., "vintage", "minimalist", "cartoon")'
    )
    
    parser.add_argument(
        '--upload',
        action='store_true',
        help='Upload to Printful and Shopify after generation'
    )
    
    parser.add_argument(
        '--count',
        type=int,
        default=1,
        help='Number of variations to generate (default: 1)'
    )
    
    args = parser.parse_args()
    
    # Generate design(s)
    for i in range(args.count):
        if args.count > 1:
            print(f"\n=== Generating design {i + 1} of {args.count} ===")
        
        design = generate_custom_design(args.prompt, args.style)
        
        if design:
            if args.upload:
                # Upload to stores
                printful_id = upload_to_printful(design)
                shopify_id = create_shopify_product(design, printful_id)
                
                print(f"Printful product ID: {printful_id}")
                print(f"Shopify product ID: {shopify_id}")
            
            # Log the generation
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": "custom",
                "design": {
                    "filename": design["filename"],
                    "category": "custom",
                    "theme": design["theme"],
                    "custom_prompt": design["custom_prompt"],
                    "style_hint": design["style_hint"]
                },
                "uploaded": args.upload
            }
            
            # Append to log
            log_filename = "generation_log.json"
            logs = []
            
            try:
                with open(log_filename, 'r') as f:
                    logs = json.load(f)
            except:
                pass
            
            logs.append(log_entry)
            
            with open(log_filename, 'w') as f:
                json.dump(logs, f, indent=2)
            
            print(f"\n✅ Success! Design saved as: {design['filename']}")
        else:
            print("\n❌ Failed to generate design")
            sys.exit(1)

if __name__ == "__main__":
    main()
