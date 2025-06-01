README.md
markdown# T-Shirt UK Automation Pipeline

Automated daily T-shirt design generation and e-commerce management for tshirt.uk.

## Quick Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt

Configure environment:
bashcp config.example.env .env
# Edit .env with your API keys

Create collections (one-time):
bashpython seed_collections.py

Test generation:
bashpython generate_tee.py


Scripts

generate_tee.py - Daily automation (runs via GitHub Actions at 08:00 UK time)
seed_collections.py - One-time collection setup
bulk_generate.py --count 5 --categories brit-pride,christmas - Bulk catalogue filling

GitHub Actions

Add repository secrets: OPENAI_API_KEY, SHOPIFY_STORE, SHOPIFY_ACCESS_TOKEN, PRINTFUL_API_KEY, MARKUP_PERCENT
Push to main branch - daily automation runs automatically at 08:00 UK time

Generates 15 designs daily (one per collection), uploads to Printful, syncs to Shopify with smart tagging and collection assignment. Focused on British culture, humor, and commercially viable niches.
