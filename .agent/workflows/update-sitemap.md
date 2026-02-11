---
description: Scan routes from src/index.html and regenerate sitemap.xml with today's date
---

# Update Sitemap Workflow

This workflow scans all client-side routes defined in `src/index.html` and regenerates `sitemap.xml`.

## Steps

1. Open `src/index.html` and find all `<a>` tags with the `data-link` attribute. Extract the `href` values — these are the application's routes (e.g., `/`, `/about`, `/references`).

2. Regenerate `sitemap.xml` using the following rules:
   - Base URL: `https://marketowl.net`
   - `lastmod`: today's date in `YYYY-MM-DD` format
   - For the root route `/`:
     - `changefreq`: `daily`
     - `priority`: `1.0`
   - For all other routes:
     - `changefreq`: `monthly`
     - `priority`: `0.8` for the first non-root route, `0.7` for subsequent routes

3. Write the updated sitemap to `sitemap.xml` in the project root, using the standard XML sitemap schema (`http://www.sitemaps.org/schemas/sitemap/0.9`).

4. Show the user the final contents of `sitemap.xml` for confirmation.
