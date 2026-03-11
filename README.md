# Shopify Products To CSV

CLI tool to discover Shopify product URLs via sitemap files, scrape product data, and write a Shopify import-ready CSV.

## Usage

```bash
python3 -m shopify_csv_cli your-store.com --output products.csv
```

Or, after installation:

```bash
python3 -m pip install -e .
shopify-products-to-csv your-store.com --output products.csv
```

## Options

- `--output`: Output CSV path (default: `products.csv`)
- `--template`: Optional CSV template path (defaults to local `product_template.csv` if present)
- `--timeout`: HTTP timeout per request in seconds (default: `10`)
- `--retries`: Number of retries for failed HTTP requests (default: `2`)
- `--delay-ms`: Delay between product requests in milliseconds (default: `150`)
- `--max-products`: Limit number of products processed
- `--verbose`: Print progress details

## Development

```bash
python3 -m pip install -e .
python3 -m unittest discover -s tests -v
```

## Open Source

- License: [MIT](./LICENSE)
- Contributing guide: [CONTRIBUTING.md](./CONTRIBUTING.md)
- Code of conduct: [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)
- Security policy: [SECURITY.md](./SECURITY.md)
