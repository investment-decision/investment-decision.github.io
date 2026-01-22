minify ./src/index.js > ./index.min.js
minify ./src/index.html > ./index.html
minify ./src/index.css > ./index.css

git add .
git commit -m "Automated minification commit"
git pull --rebase origin main && git push origin main