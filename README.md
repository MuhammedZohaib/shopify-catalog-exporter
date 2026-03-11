# Shopify Sitemap To CSV

CLI tool to discover Shopify product URLs via sitemap files, scrape product data, and write a Shopify import-ready CSV.

## Usage

```bash
python -m shopify_csv_cli your-store.com --output products.csv
```

Or, after installation:

```bash
shopify-sitemap-to-csv your-store.com --output products.csv
```

## Options

- `--output`: Output CSV path (default: `products.csv`)
- `--template`: Optional CSV template path (defaults to local `product_template.csv` if present)
- `--timeout`: HTTP timeout per request in seconds (default: `10`)
- `--retries`: Number of retries for failed HTTP requests (default: `2`)
- `--delay-ms`: Delay between product requests in milliseconds (default: `150`)
- `--max-products`: Limit number of products processed
- `--verbose`: Print progress details
