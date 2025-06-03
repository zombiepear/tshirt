# T-Shirt Design Generator - Improvements

## 🎯 Key Fixes

### Fixed Multiple Image Problem
The main issue of designs containing multiple versions/comparisons has been fixed by:

1. **Explicit Single Design Instructions**: Every prompt now explicitly states to create "ONE unified design" and "no multiple versions, comparisons, or split compositions"

2. **Anti-Duplication Language**: Added specific instructions against creating:
   - Multiple panels
   - Before/after comparisons
   - Split screens
   - Multiple variations

3. **Technical Specifications**: Clear requirements for:
   - Single, centered composition
   - One cohesive design element
   - No panels or variations

## 🎨 New Categories Added

The following categories have been added to the generator:

- **Party** - Disco balls, neon lights, celebration themes
- **Anniversary** - Romantic celebrations, milestone moments
- **British Humour** - Tea time chaos, queue jumping, dry wit
- **Birthday** - Cake explosions, party hats, birthday vibes
- **Christmas** - Santa's workshop, winter wonderland, festive themes
- **Summer** - Beach vibes, tropical drinks, sunshine
- **Winter** - Cozy fireplaces, snowflakes, winter sports
- **Memes** - Internet culture, viral moments, trending topics

## 📁 Files Included

1. **generate_tee.py** - Main generator with fixed prompts
2. **bulk_generate.py** - Bulk generation with category selection
3. **collections.json** - All categories with themes and tags
4. **requirements.txt** - Python dependencies
5. **.github/workflows/generate-tshirt.yml** - Automated workflow
6. **.github/workflows/manual-generate.yml** - Manual trigger workflow

## 🚀 How to Use

1. **Set up GitHub Secrets**:
   - `OPENAI_API_KEY` - Your OpenAI API key
   - `PRINTFUL_API_KEY` - Your Printful Bearer token
   - `PRINTFUL_STORE_ID` - Your Printful store ID (optional)
   - `SHOPIFY_STORE` - Your Shopify store name
   - `SHOPIFY_ACCESS_TOKEN` - Your Shopify Admin API token
   - `MARKUP_PERCENT` - Price markup (e.g., 1.4 for 40%)

2. **Automatic Generation**:
   - Pushes to main branch trigger generation
   - Daily generation at 10 AM UTC
   - Generates random category designs

3. **Manual Generation**:
   - Go to Actions → Manual T-Shirt Generation
   - Select category (or random)
   - Choose number of designs (1-20)
   - Set delay between generations

## 🎯 Example Prompts

The new prompts ensure single designs by using language like:

```
Create a SINGLE, professional t-shirt design...
CRITICAL: Generate only ONE unified design - absolutely no multiple versions...
```

## 📊 Categories Overview

Total categories: **15**
- Original: gaming, nature, abstract, vintage, fitness, coffee, music
- New: party, anniversary, british-humour, birthday, christmas, summer, winter, memes

Each category has:
- 10 unique themes
- Specific style guidelines
- Relevant tags for SEO

## 🔧 Technical Improvements

1. **Better Error Handling**: Comprehensive try-catch blocks
2. **Detailed Logging**: JSON logs for all generations
3. **Bulk Generation**: Generate multiple designs efficiently
4. **GitHub Actions Integration**: Full CI/CD pipeline
5. **Artifact Storage**: Automatic storage of designs and logs
