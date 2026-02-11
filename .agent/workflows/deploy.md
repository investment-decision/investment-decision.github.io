---
description: Build (minify) source files and deploy to GitHub Pages via git push
---

# Deploy Workflow

This workflow minifies the source files in `src/`, copies `index.html` to `404.html`, then commits and pushes to GitHub Pages.

## Steps

1. Minify JavaScript
// turbo
```bash
minify ./src/index.js > ./index.min.js
```

2. Minify HTML
// turbo
```bash
minify ./src/index.html > ./index.html
```

3. Minify CSS
// turbo
```bash
minify ./src/index.css > ./index.css
```

4. Copy index.html to 404.html (for SPA routing)
// turbo
```bash
cp ./index.html ./404.html
```

5. Stage all changes
```bash
git add .
```

6. Commit with a descriptive message
```bash
git commit -m "Build and deploy $(date '+%Y-%m-%d %H:%M:%S')"
```

7. Pull with rebase and push to main
```bash
git pull --rebase origin main && git push origin main
```
