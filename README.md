# T-Shirt Generator for GitHub Actions 🎨👕

Automated T-shirt design generator using AI (DALL-E 3) with Printful and Shopify integration.
Designed specifically for GitHub Actions - no local setup needed!

## Setup

### 1. Add Repository Secrets

Go to **Settings** → **Secrets and variables** → **Actions** and add:

- `OPENAI_API_KEY` - Your OpenAI API key
- `PRINTFUL_API_KEY` - Your Printful Bearer token (OAuth)
- `PRINTFUL_STORE_ID` - Your Printful store ID (optional)
- `SHOPIFY_STORE` - Your Shopify store name (without .myshopify.com)
- `SHOPIFY_ACCESS_TOKEN` - Your Shopify Admin API access token
- `MARKUP_PERCENT` - Price markup (e.g., 1.4 for 40% markup)

### 2. Add Files to Repository

Copy all these files to your repository:
- `generate_tee.py` - Main generator
- `bulk_generate.py` - Bulk generation
- `collections.json` - Design categories
- `requirements.txt` - Python dependencies
- `.github/workflows/generate-tshirt.yml` - Automatic workflow
- `.github/workflows/manual-generate.yml` - Manual workflow

### 3. That's It!

The workflows will run automatically on:
- Push to main branch
- Daily at 10 AM UTC
- Manual trigger from Actions tab

## Usage

### Automatic Generation

Happens automatically when you push code or on schedule.

### Manual Generation

1. Go to **Actions** tab
2. Select **Manual T-Shirt Generation**
3. Click **Run workflow**
4. Options:
   - **Category**: Leave empty for random, or specify (e.g., `gaming`)
   - **Count**: Number of designs (default: 1)
   - **Delay**: Seconds between designs (default: 5)

### View Results

After each run:
1. Go to the workflow run
2. Download artifacts at the bottom
3. Contains:
   - Generated PNG files
   - Log file with details

## Available Categories

- `birthday-party` - Birthday celebrations
- `christmas-festive` - Holiday designs
- `gaming` - Gaming culture
- `fitness` - Gym & workout
- `coffee` - Coffee lovers
- `foodie` - Food enthusiasts
- `dad-jokes` - Dad humor
- `sarcastic` - Sarcastic humor
- `music` - Music lovers
- `positive-vibes` - Positive motivation

## Important Notes

### Printful Setup
- Must use a "Manual Order/API" platform store
- Use OAuth Bearer token (not old API key)

### Shopify Setup (Optional)
- Create private app with Products read/write
- Use Admin API access token

## Troubleshooting

### "Missing API keys" Error
Check that your workflow has the `env:` section:
```yaml
env:
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  PRINTFUL_API_KEY: ${{ secrets.PRINTFUL_API_KEY }}
  # etc...
```

### Check Logs
Download artifacts after each run to see detailed logs.

## No Local Setup Needed!

Everything runs in GitHub Actions. No need for:
- Local Python installation
- .env files
- API key files

Just add your secrets and push the code! 🚀
