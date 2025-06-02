name: Debug Printful Connection

on:
  workflow_dispatch:

jobs:
  debug:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - uses: actions/setup-python@v4
      with:
        python-version: '3.x'
    
    - name: Install requests
      run: pip install requests
    
    - name: Debug Printful API
      env:
        PRINTFUL_API_KEY: ${{ secrets.PRINTFUL_API_KEY }}
      run: |
        # First create the debug script
        cat > debug_printful.py << 'EOF'
        import os
        import requests
        import json
        
        print("🔍 Debugging Printful API Connection\\n")
        
        api_key = os.environ.get('PRINTFUL_API_KEY')
        if not api_key:
            print("❌ PRINTFUL_API_KEY not found")
            exit(1)
        
        print(f"Token length: {len(api_key)} characters")
        print(f"Token preview: {api_key[:10]}...{api_key[-5:]}")
        
        if "-" in api_key and len(api_key) == 36:
            print("⚠️  WARNING: This looks like an old UUID-style API key!")
        else:
            print("✅ Token format looks correct")
        
        headers = {"Authorization": f"Bearer {api_key}"}
        
        response = requests.get("https://api.printful.com/store", headers=headers)
        print(f"\\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            store = response.json().get('result', {})
            print(f"✅ Connected to: {store.get('name', 'Unknown')}")
            print(f"Store Type: {store.get('type', 'Unknown')}")
        else:
            print(f"❌ Error: {response.text[:200]}")
        EOF
        
        python debug_printful.py
