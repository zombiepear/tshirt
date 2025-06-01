#!/usr/bin/env python3
"""
Working Printful T-Shirt Generator
Fixed to match your original working code with proper environment variables
"""

import os
import json
import random
import logging
import requests
import base64
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging with detailed formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('tshirt_generator.log')
    ]
)
logger = logging.getLogger(__name__)

class TShirtGenerator:
    def __init__(self):
        """Initialize with proper API configurations."""
        # API Keys from environment - supporting both naming conventions
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        # Printful - try both PRINTFUL_API_KEY (GitHub secret) and PRINTFUL_API_TOKEN
        self.printful_api_token = os.getenv('PRINTFUL_API_KEY') or os.getenv('PRINTFUL_API_TOKEN')
        
        # Shopify - support both old and new formats
        self.shopify_store_name = os.getenv('SHOPIFY_STORE') or os.getenv('SHOPIFY_STORE_NAME')
        
        # For Shopify auth, check for access token first (new way), then API key/password (old way)
        self.shopify_access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        self.shopify_api_key = os.getenv('SHOPIFY_API_KEY')
        self.shopify_password = os.getenv('SHOPIFY_PASSWORD')
        
        # Pricing
        self.markup_percent = float(os.getenv('MARKUP_PERCENT', '1.4'))
        
        if not all([self.openai_api_key, self.printful_api_token]):
            raise ValueError("Missing required API keys (OPENAI_API_KEY and PRINTFUL_API_KEY/TOKEN)")
        
        # Initialize OpenAI
        self.openai_client = OpenAI(api_key=self.openai_api_key)
        
        # Printful configuration
        self.printful_base_url = "https://api.printful.com"
        self.printful_headers = {
            "Authorization": f"Bearer {self.printful_api_token}",
            "Content-Type": "application/json",
            "User-Agent": "TShirtGenerator/1.0"
        }
        
        # Valid Bella+Canvas 3001 variant IDs (verified from API docs)
        self.bella_canvas_variants = {
            'white_s': 4011,
            'white_m': 4012, 
            'white_l': 4013,
            'white_xl': 4014,
            'black_s': 4016,
            'black_m': 4017,
            'black_l': 4018,
            'black_xl': 4019
        }
        
        # Load design collections
        self.collections = self._load_collections()
        
        # Verify Printful store setup
        self._verify_printful_store()
    
    def _load_collections(self) -> Dict:
        """Load design collections from file."""
        try:
            if os.path.exists('collections.json'):
                with open('collections.json', 'r') as f:
                    collections = json.load(f)
                logger.info(f"✅ Loaded {len(collections)} collections")
                return collections
            else:
                logger.warning("⚠️ No collections.json found, using default collection")
                return {
                    "birthday-party": {
                        "theme": "Birthday party t-shirt design, cake, balloons, party hats, funny age jokes, birthday wishes",
                        "title": "Birthday Celebrations",
                        "name": "Birthday Celebrations",
                        "tags": ["birthday", "party", "celebration", "fun"]
                    }
                }
        except Exception as e:
            logger.error(f"❌ Error loading collections: {e}")
            return {}
    
    def _verify_printful_store(self) -> None:
        """Verify Printful store configuration and API access."""
        try:
            # Test API access
            response = requests.get(
                f"{self.printful_base_url}/store",
                headers=self.printful_headers,
                timeout=30
            )
            
            if response.status_code == 200:
                store_data = response.json()
                logger.info("✅ Printful API access verified")
                
                # Check store platform
                if 'result' in store_data:
                    platform = store_data['result'].get('platform')
                    store_name = store_data['result'].get('name', 'Unknown')
                    
                    logger.info(f"📋 Store: {store_name}")
                    logger.info(f"📋 Platform: {platform}")
                    
                    # Critical check: Must be Manual Order/API platform
                    if platform and platform.lower() not in ['api', 'manual']:
                        logger.error(f"❌ CRITICAL: Store platform is '{platform}'")
                        logger.error("❌ Product creation only works with 'Manual Order/
