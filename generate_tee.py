#!/usr/bin/env python3
"""
T-Shirt Design Generator
Generates unique t-shirt designs using DALL-E 3 and uploads to Printful/Shopify
"""

import os
import json
import time
import random
import requests
from datetime import datetime
from openai import OpenAI
import base64
from io import BytesIO
from PIL import Image

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Configuration
PRINTFUL_API_KEY = os.environ.get("PRINTFUL_API_KEY")
PRINTFUL_STORE_ID = os.environ.get("PRINTFUL_STORE_ID")
SHOPIFY_STORE = os.environ.get("SHOPIFY_STORE")
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN")
MARKUP_PERCENT = float(os.environ.get("MARKUP_PERCENT", "1.4"))

# Printful API endpoints
PRINTFUL_API_BASE = "https://api.printful.com"
SHOPIFY_API_BASE = f"https://{SHOPIFY_STORE}.myshopify.com/admin/api/2024-01"

# Design categories with themes
DESIGN_CATEGORIES = {
    "gaming": {
        "themes": ["retro arcade", "RPG adventure", "pixel art", "gaming controller", "achievement unlocked", 
                   "game over", "respawn", "boss battle", "speed run", "gaming setup"],
        "style": "modern gaming aesthetic with vibrant colors"
    },
    "nature": {
        "themes": ["mountain landscape", "ocean waves", "forest scene", "sunset view", "wildlife", 
                   "camping adventure", "starry night", "desert cactus", "tropical paradise", "aurora borealis"],
        "style": "natural beauty with organic shapes"
    },
    "abstract": {
        "themes": ["geometric patterns", "fluid dynamics", "color explosion", "minimalist shapes", 
                   "optical illusion", "sacred geometry", "wave patterns", "crystalline structures", 
                   "mandala design", "fractal art"],
        "style": "modern abstract art with bold composition"
    },
    "vintage": {
        "themes": ["retro typography", "classic car", "old school radio", "vintage camera", 
                   "record player", "typewriter", "antique telephone", "retro diner", 
                   "vintage motorcycle", "classic movie poster"],
        "style": "distressed retro aesthetic with weathered effects"
    },
    "party": {
        "themes": ["disco ball", "neon lights party", "confetti celebration", "dance floor vibes", 
                   "party animals", "celebration time", "festival mood", "birthday bash", 
                   "cocktail party", "rave culture"],
        "style": "vibrant party atmosphere with energetic design"
    },
    "anniversary": {
        "themes": ["love celebration", "milestone moment", "golden anniversary", "silver jubilee", 
                   "romantic celebration", "years together", "eternal bond", "anniversary roses", 
                   "champagne toast", "timeless love"],
        "style": "elegant and romantic with sophisticated touches"
    },
    "british-humour": {
        "themes": ["tea time chaos", "queue jumping scandal", "weather complaints", "british bulldog", 
                   "keep calm parody", "full english breakfast", "london underground", "rainy day mood", 
                   "pub culture", "british sarcasm"],
        "style": "witty British design with dry humor elements"
    },
    "birthday": {
        "themes": ["birthday cake explosion", "party hat fun", "balloon celebration", "birthday squad", 
                   "aging like wine", "birthday king/queen", "make a wish", "another year wiser", 
                   "birthday vibes", "cake and confetti"],
        "style": "festive birthday design with celebratory elements"
    },
    "christmas": {
        "themes": ["santa's workshop", "christmas tree magic", "winter wonderland", "reindeer games", 
                   "ugly sweater pattern", "holiday cheer", "snowman party", "christmas lights", 
                   "gingerbread house", "festive ornaments"],
        "style": "festive holiday design with Christmas spirit"
    },
    "summer": {
        "themes": ["beach vibes", "summer sunset", "tropical drinks", "surfing waves", "ice cream truck", 
                   "pool party", "summer road trip", "beach volleyball", "sunshine state", "summer festival"],
        "style": "bright summer aesthetic with warm colors"
    },
    "winter": {
        "themes": ["cozy fireplace", "snowflake pattern", "winter cabin", "hot chocolate mood", 
                   "skiing adventure", "frozen landscape", "winter wildlife", "ice skating", 
                   "snowy mountains", "aurora winter"],
        "style": "cool winter design with icy elements"
    },
    "memes": {
        "themes": ["internet culture", "viral moment", "meme lord", "dank vibes", "trending now", 
                   "social media chaos", "emoji overload", "hashtag life", "viral sensation", 
                   "meme energy"],
        "style": "modern internet culture with meme aesthetics"
    },
    "fitness": {
        "themes": ["gym motivation", "workout warrior", "fitness journey", "muscle power", 
                   "cardio queen", "lift heavy", "fitness goals", "sweat equity", "gym life", "beast mode"],
        "style": "energetic fitness design with motivational elements"
    },
    "coffee": {
        "themes": ["coffee addiction", "espresso yourself", "coffee beans", "cafe vibes", 
                   "morning ritual", "coffee chemistry", "latte art", "coffee shop", "caffeine molecule", 
                   "coffee lover"],
        "style": "warm coffee-themed design with cozy elements"
    },
    "music": {
        "themes": ["sound waves", "vinyl records", "guitar hero", "music festival", "headphones on", 
                   "piano keys", "music notes", "concert vibes", "DJ setup", "rock and roll"],
        "style": "musical design with rhythm and flow"
    }
}

def generate_design_prompt(category_name, theme, style):
    """Generate an optimized prompt for single t-shirt designs"""
    
    prompt = f"""Create a SINGLE, professional t-shirt design with these exact specifications:

CRITICAL: Generate only ONE unified design - absolutely no multiple versions, comparisons, or split compositions.

Design Requirements:
- Theme: {theme}
- Style: {style}
- Category: {category_name}

Technical Specifications:
- Single, centered composition filling the canvas
- Clean edges suitable for direct fabric printing
- Bold, eye-catching artwork that stands out on clothing
- Professional vector-style or artistic illustration
- Transparent or white background
- High contrast for good print reproduction
- One cohesive design element - no panels or variations

IMPORTANT: The entire 1024x1024 image must be ONE complete design suitable for t-shirt printing. 
Do not create multiple options, before/after, or comparison layouts."""

    return prompt

def generate_design(category=None):
    """Generate a single t-shirt design"""
    
    # Select random category if not specified
    if not category:
        category = random.choice(list(DESIGN_CATEGORIES.keys()))
    
    # Get category details
    category_info = DESIGN_CATEGORIES.get(category, DESIGN_CATEGORIES["abstract"])
    theme = random.choice(category_info["themes"])
    style = category_info["style"]
    
    # Generate the design prompt
    prompt = generate_design_prompt(category, theme, style)
    
    print(f"Generating design for category: {category}")
    print(f"Theme: {theme}")
    print(f"Prompt: {prompt[:200]}...")
    
    try:
        # Generate image with DALL-E 3
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            style="vivid",
            n=1  # Always generate only 1 image
        )
        
        image_url = response.data[0].url
        revised_prompt = response.data[0].revised_prompt
        
        print(f"Design generated successfully!")
        print(f"Revised prompt: {revised_prompt[:200]}...")
        
        # Download the image
        image_response = requests.get(image_url)
        image_response.raise_for_status()
        
        # Save the image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"design_{category}_{theme.replace(' ', '_')}_{timestamp}.png"
        
        with open(filename, 'wb') as f:
            f.write(image_response.content)
        
        print(f"Design saved as: {filename}")
        
        return {
            "filename": filename,
            "category": category,
            "theme": theme,
            "prompt": prompt,
            "revised_prompt": revised_prompt,
            "image_url": image_url,
            "image_data": image_response.content
        }
        
    except Exception as e:
        print(f"Error generating design: {str(e)}")
        return None

def upload_to_printful(design_data):
    """Upload design to Printful"""
    
    if not PRINTFUL_API_KEY:
        print("Printful API key not configured, skipping upload")
        return None
    
    headers = {
        "Authorization": f"Bearer {PRINTFUL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # First, upload the image file
        files_url = f"{PRINTFUL_API_BASE}/files"
        
        # Convert image to base64
        image_base64 = base64.b64encode(design_data["image_data"]).decode('utf-8')
        
        file_data = {
            "name": design_data["filename"],
            "contents": f"data:image/png;base64,{image_base64}"
        }
        
        response = requests.post(files_url, json=file_data, headers=headers)
        response.raise_for_status()
        
        file_id = response.json()["result"]["id"]
        print(f"File uploaded to Printful with ID: {file_id}")
        
        # Create a product
        product_data = {
            "sync_product": {
                "name": f"{design_data['category'].title()} - {design_data['theme'].title()}",
                "thumbnail": f"data:image/png;base64,{image_base64[:1000]}..."  # Truncated for thumbnail
            },
            "sync_variants": [
                {
                    "variant_id": 4012,  # Unisex Staple T-Shirt (Bella + Canvas 3001) - S
                    "retail_price": "25.00",
                    "files": [
                        {
                            "id": file_id,
                            "type": "default"
                        }
                    ]
                },
                {
                    "variant_id": 4013,  # M
                    "retail_price": "25.00",
                    "files": [{"id": file_id, "type": "default"}]
                },
                {
                    "variant_id": 4014,  # L
                    "retail_price": "25.00",
                    "files": [{"id": file_id, "type": "default"}]
                },
                {
                    "variant_id": 4015,  # XL
                    "retail_price": "25.00",
                    "files": [{"id": file_id, "type": "default"}]
                },
                {
                    "variant_id": 4016,  # 2XL
                    "retail_price": "28.00",
                    "files": [{"id": file_id, "type": "default"}]
                }
            ]
        }
        
        # Add store ID if configured
        if PRINTFUL_STORE_ID:
            product_url = f"{PRINTFUL_API_BASE}/store/{PRINTFUL_STORE_ID}/products"
        else:
            product_url = f"{PRINTFUL_API_BASE}/sync/products"
        
        response = requests.post(product_url, json=product_data, headers=headers)
        response.raise_for_status()
        
        product_id = response.json()["result"]["id"]
        print(f"Product created in Printful with ID: {product_id}")
        
        return product_id
        
    except Exception as e:
        print(f"Error uploading to Printful: {str(e)}")
        return None

def create_shopify_product(design_data, printful_product_id=None):
    """Create product in Shopify"""
    
    if not SHOPIFY_STORE or not SHOPIFY_ACCESS_TOKEN:
        print("Shopify not configured, skipping product creation")
        return None
    
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    try:
        # Calculate prices with markup
        base_price = 25.00
        retail_price = round(base_price * MARKUP_PERCENT, 2)
        
        product_data = {
            "product": {
                "title": f"{design_data['category'].title()} T-Shirt - {design_data['theme'].title()}",
                "body_html": f"<p>Unique {design_data['category']} themed t-shirt featuring {design_data['theme']}.</p><p>Designed with AI and printed on demand on high-quality fabric.</p>",
                "vendor": "AI Designs",
                "product_type": "T-Shirt",
                "tags": f"{design_data['category']}, ai-generated, t-shirt, {design_data['theme']}",
                "variants": [
                    {"option1": "S", "price": str(retail_price), "sku": f"TEE-{design_data['category']}-S"},
                    {"option1": "M", "price": str(retail_price), "sku": f"TEE-{design_data['category']}-M"},
                    {"option1": "L", "price": str(retail_price), "sku": f"TEE-{design_data['category']}-L"},
                    {"option1": "XL", "price": str(retail_price), "sku": f"TEE-{design_data['category']}-XL"},
                    {"option1": "2XL", "price": str(round(retail_price * 1.12, 2)), "sku": f"TEE-{design_data['category']}-2XL"}
                ],
                "options": [
                    {"name": "Size", "values": ["S", "M", "L", "XL", "2XL"]}
                ]
            }
        }
        
        url = f"{SHOPIFY_API_BASE}/products.json"
        response = requests.post(url, json=product_data, headers=headers)
        response.raise_for_status()
        
        shopify_product = response.json()["product"]
        print(f"Product created in Shopify: {shopify_product['title']}")
        
        return shopify_product["id"]
        
    except Exception as e:
        print(f"Error creating Shopify product: {str(e)}")
        return None

def main():
    """Main function to generate and upload design"""
    
    print("=== T-Shirt Design Generator ===")
    print(f"Available categories: {', '.join(DESIGN_CATEGORIES.keys())}")
    
    # Generate design
    design = generate_design()
    
    if design:
        # Upload to Printful
        printful_id = upload_to_printful(design)
        
        # Create Shopify product
        shopify_id = create_shopify_product(design, printful_id)
        
        # Log results
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "design": {
                "filename": design["filename"],
                "category": design["category"],
                "theme": design["theme"],
                "prompt": design["prompt"]
            },
            "printful_product_id": printful_id,
            "shopify_product_id": shopify_id
        }
        
        # Append to log file
        log_filename = "generation_log.json"
        logs = []
        
        if os.path.exists(log_filename):
            with open(log_filename, 'r') as f:
                logs = json.load(f)
        
        logs.append(log_data)
        
        with open(log_filename, 'w') as f:
            json.dump(logs, f, indent=2)
        
        print(f"\nGeneration complete! Check {log_filename} for details.")
        
    else:
        print("Failed to generate design")

if __name__ == "__main__":
    main()
