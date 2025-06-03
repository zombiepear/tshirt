name: Generate T-Shirt Design

on:
  workflow_dispatch:
  push:
    branches: [ main ]
    paths-ignore:
      - 'designs/**'  # Don't trigger on design commits
      - '*.log'
  schedule:
    - cron: '0 10 * * *'

jobs:
  generate:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
      with:
        fetch-depth: 0
        token: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install openai==1.12.0 requests==2.31.0 Pillow==10.0.0
        python -c "import openai; print(f'OpenAI version: {openai.__version__}')"
    
    - name: Create designs directory
      run: mkdir -p designs
    
    - name: Run T-Shirt Generator
      env:
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        PRINTFUL_API_KEY: ${{ secrets.PRINTFUL_API_KEY }}
        PRINTFUL_STORE_ID: ${{ secrets.PRINTFUL_STORE_ID }}
        MARKUP_PERCENT: ${{ secrets.MARKUP_PERCENT }}
        GITHUB_REPOSITORY: ${{ github.repository }}
      run: |
        echo "🎨 Generating T-Shirt Design..."
        echo "📍 Repository: $GITHUB_REPOSITORY"
        python generate_tee.py
    
    - name: Commit and push designs
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        
        # Pull latest changes first (in case multiple workflows running)
        echo "📥 Pulling latest changes..."
        git pull origin main --rebase
        
        # Check what files were generated
        echo "📁 Generated files:"
        ls -la designs/*.png 2>/dev/null || echo "No new PNG files"
        
        # Add all generated files
        git add designs/*.png designs/*.json || true
        git add *.log || true
        
        # Commit and push with conflict handling
        if git diff --staged --quiet; then
          echo "No new files to commit"
        else
          git commit -m "🎨 Add design from run ${{ github.run_number }} [skip ci]"
          
          # Push with retry logic
          RETRY=0
          MAX_RETRIES=3
          while [ $RETRY -lt $MAX_RETRIES ]; do
            if git push origin main; then
              echo "✅ Push successful!"
              break
            else
              RETRY=$((RETRY + 1))
              if [ $RETRY -eq $MAX_RETRIES ]; then
                echo "❌ Failed to push after $MAX_RETRIES attempts"
                exit 1
              fi
              echo "⚠️ Push failed, attempt $RETRY/$MAX_RETRIES. Pulling and retrying..."
              git pull origin main --rebase
              sleep $((RETRY * 2))
            fi
          done
        fi
    
    - name: Create/Update Gallery
      run: |
        cat > index.html << 'EOF'
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AI T-Shirt Designs</title>
            <meta name="description" content="Daily AI-generated t-shirt designs">
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    background: #f8f9fa;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }
                header {
                    text-align: center;
                    padding: 40px 0;
                    background: white;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    margin-bottom: 40px;
                }
                h1 {
                    color: #2c3e50;
                    font-size: 2.5em;
                    margin-bottom: 10px;
                }
                .subtitle {
                    color: #7f8c8d;
                    font-size: 1.2em;
                }
                .filters {
                    text-align: center;
                    margin-bottom: 30px;
                }
                .filter-btn {
                    background: #3498db;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    margin: 5px;
                    border-radius: 25px;
                    cursor: pointer;
                    transition: all 0.3s;
                }
                .filter-btn:hover { background: #2980b9; }
                .filter-btn.active { background: #2c3e50; }
                .gallery {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 30px;
                    padding: 20px 0;
                }
                .design-card {
                    background: white;
                    border-radius: 10px;
                    overflow: hidden;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                    transition: all 0.3s;
                    cursor: pointer;
                }
                .design-card:hover {
                    transform: translateY(-5px);
                    box-shadow: 0 10px 30px rgba(0,0,0,0.15);
                }
                .design-card img {
                    width: 100%;
                    height: 350px;
                    object-fit: cover;
                    background: #f0f0f0;
                }
                .design-info {
                    padding: 20px;
                }
                .design-title {
                    font-size: 1.2em;
                    font-weight: 600;
                    margin-bottom: 8px;
                    color: #2c3e50;
                }
                .design-meta {
                    display: flex;
                    justify-content: space-between;
                    color: #7f8c8d;
                    font-size: 0.9em;
                }
                .loading {
                    text-align: center;
                    padding: 100px 20px;
                    color: #7f8c8d;
                }
                .error {
                    background: #fee;
                    color: #c33;
                    padding: 20px;
                    border-radius: 5px;
                    margin: 20px auto;
                    max-width: 600px;
                    text-align: center;
                }
                footer {
                    text-align: center;
                    padding: 40px 20px;
                    color: #7f8c8d;
                    margin-top: 60px;
                    border-top: 1px solid #e0e0e0;
                }
                footer a {
                    color: #3498db;
                    text-decoration: none;
                }
                footer a:hover { text-decoration: underline; }
                
                /* Modal */
                .modal {
                    display: none;
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0,0,0,0.9);
                    z-index: 1000;
                    cursor: pointer;
                }
                .modal img {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    max-width: 90%;
                    max-height: 90%;
                    box-shadow: 0 0 30px rgba(0,0,0,0.5);
                }
                .modal.active { display: block; }
            </style>
        </head>
        <body>
            <header>
                <div class="container">
                    <h1>🎨 AI T-Shirt Design Gallery</h1>
                    <p class="subtitle">Fresh designs generated daily with DALL-E 3</p>
                </div>
            </header>
            
            <div class="container">
                <div class="filters">
                    <button class="filter-btn active" data-filter="all">All Designs</button>
                    <button class="filter-btn" data-filter="birthday-party">Birthday</button>
                    <button class="filter-btn" data-filter="retro-gaming">Gaming</button>
                    <button class="filter-btn" data-filter="nature-inspired">Nature</button>
                    <button class="filter-btn" data-filter="funny-slogans">Funny</button>
                    <button class="filter-btn" data-filter="abstract-art">Abstract</button>
                </div>
                
                <div id="loading" class="loading">
                    <p>Loading amazing designs...</p>
                </div>
                
                <div id="gallery" class="gallery" style="display: none;"></div>
                
                <div id="error" class="error" style="display: none;"></div>
            </div>
            
            <footer>
                <p>Generated with ❤️ by AI | Hosted on GitHub Pages</p>
                <p><a href="https://github.com/${{ github.repository }}">View on GitHub</a> | 
                   <a href="https://github.com/${{ github.repository }}/tree/main/designs">Browse Files</a></p>
            </footer>
            
            <div id="modal" class="modal">
                <img id="modalImg" src="" alt="">
            </div>
            
            <script>
                const modal = document.getElementById('modal');
                const modalImg = document.getElementById('modalImg');
                let allDesigns = [];
                
                async function loadDesigns() {
                    const gallery = document.getElementById('gallery');
                    const loading = document.getElementById('loading');
                    const errorDiv = document.getElementById('error');
                    
                    try {
                        const response = await fetch('designs/');
                        if (!response.ok) throw new Error('Could not load designs');
                        
                        const html = await response.text();
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(html, 'text/html');
                        const links = Array.from(doc.querySelectorAll('a'));
                        
                        allDesigns = links
                            .filter(link => link.href.endsWith('.png'))
                            .map(link => {
                                const filename = link.textContent;
                                const match = filename.match(/(.+?)_(\d{8})_(\d{6})\.png/);
                                
                                return {
                                    url: link.href,
                                    filename: filename,
                                    collection: match ? match[1] : 'design',
                                    date: match ? formatDate(match[2]) : 'Unknown date',
                                    timestamp: match ? match[2] + match[3] : '0'
                                };
                            })
                            .sort((a, b) => b.timestamp - a.timestamp);
                        
                        if (allDesigns.length === 0) {
                            throw new Error('No designs found yet. Check back soon!');
                        }
                        
                        displayDesigns(allDesigns);
                        loading.style.display = 'none';
                        gallery.style.display = 'grid';
                        
                    } catch (error) {
                        console.error('Error:', error);
                        errorDiv.textContent = error.message;
                        errorDiv.style.display = 'block';
                        loading.style.display = 'none';
                    }
                }
                
                function formatDate(dateStr) {
                    const year = dateStr.slice(0, 4);
                    const month = dateStr.slice(4, 6);
                    const day = dateStr.slice(6, 8);
                    const date = new Date(year, month - 1, day);
                    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
                }
                
                function formatTitle(collection) {
                    return collection
                        .split('-')
                        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                        .join(' ');
                }
                
                function displayDesigns(designs) {
                    const gallery = document.getElementById('gallery');
                    gallery.innerHTML = '';
                    
                    designs.forEach((design, index) => {
                        const card = document.createElement('div');
                        card.className = 'design-card';
                        card.dataset.collection = design.collection;
                        
                        card.innerHTML = `
                            <img src="${design.url}" 
                                 alt="${formatTitle(design.collection)} design" 
                                 loading="${index < 6 ? 'eager' : 'lazy'}">
                            <div class="design-info">
                                <div class="design-title">${formatTitle(design.collection)}</div>
                                <div class="design-meta">
                                    <span>${design.date}</span>
                                    <span>#${allDesigns.length - index}</span>
                                </div>
                            </div>
                        `;
                        
                        card.addEventListener('click', () => {
                            modalImg.src = design.url;
                            modal.classList.add('active');
                        });
                        
                        gallery.appendChild(card);
                    });
                }
                
                // Filter functionality
                document.querySelectorAll('.filter-btn').forEach(btn => {
                    btn.addEventListener('click', () => {
                        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                        btn.classList.add('active');
                        
                        const filter = btn.dataset.filter;
                        if (filter === 'all') {
                            displayDesigns(allDesigns);
                        } else {
                            displayDesigns(allDesigns.filter(d => d.collection === filter));
                        }
                    });
                });
                
                // Modal close
                modal.addEventListener('click', () => {
                    modal.classList.remove('active');
                });
                
                // Load designs on page load
                loadDesigns();
            </script>
        </body>
        </html>
        EOF
        
        # Commit gallery
        git add index.html || true
        git diff --staged --quiet || git commit -m "Update gallery [skip ci]"
        git push origin main || echo "Gallery push failed, continuing..."
    
    - name: Upload artifacts
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: designs-${{ github.run_number }}
        path: |
          designs/
          *.log
        retention-days: 30
        if-no-files-found: warn
    
    - name: Job Summary
      if: always()
      run: |
        echo "## 🎨 T-Shirt Generation Report" >> $GITHUB_STEP_SUMMARY
        echo "" >> $GITHUB_STEP_SUMMARY
        
        if ls designs/*.png 2>/dev/null | grep -q "$(date +%Y%m%d)"; then
          echo "### ✅ Design Generated Successfully!" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          LATEST_DESIGN=$(ls -t designs/*.png 2>/dev/null | head -1)
          if [ -n "$LATEST_DESIGN" ]; then
            echo "**Latest Design:** \`$(basename $LATEST_DESIGN)\`" >> $GITHUB_STEP_SUMMARY
          fi
        else
          echo "### ⚠️ No design generated in this run" >> $GITHUB_STEP_SUMMARY
        fi
        
        echo "" >> $GITHUB_STEP_SUMMARY
        echo "### 🔗 Links" >> $GITHUB_STEP_SUMMARY
        echo "- [View Gallery](https://zombiepear.github.io/tshirt/)" >> $GITHUB_STEP_SUMMARY
        echo "- [Browse Designs](https://github.com/zombiepear/tshirt/tree/main/designs)" >> $GITHUB_STEP_SUMMARY
        echo "- [View Logs](https://github.com/zombiepear/tshirt/actions/runs/${{ github.run_id }})" >> $GITHUB_STEP_SUMMARY
        
        echo "" >> $GITHUB_STEP_SUMMARY
        echo "### 📊 Statistics" >> $GITHUB_STEP_SUMMARY
        echo "- Total designs: $(ls designs/*.png 2>/dev/null | wc -l || echo 0)" >> $GITHUB_STEP_SUMMARY
        echo "- Run number: #${{ github.run_number }}" >> $GITHUB_STEP_SUMMARY
        echo "- Triggered by: ${{ github.event_name }}" >> $GITHUB_STEP_SUMMARY
