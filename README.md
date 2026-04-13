# shopify-catalog-exporter

Scrape any public Shopify store via its sitemap and export all products to a
Shopify Admin-compatible import CSV — no API key required.

## Install

```bash
pip install shopify-catalog-exporter
# or for faster HTTP:
pip install "shopify-catalog-exporter[requests]"
```

## Usage

```bash
shopify-catalog-export someshop.myshopify.com
shopify-catalog-export someshop.myshopify.com --output products.csv --verbose
shopify-catalog-export someshop.myshopify.com --max-products 50 --delay-ms 200
```

## Options

| Flag             | Default        | Description                 |
| ---------------- | -------------- | --------------------------- |
| `--output`       | `products.csv` | Output CSV path             |
| `--template`     | auto           | Custom CSV template path    |
| `--timeout`      | `10`           | HTTP timeout in seconds     |
| `--retries`      | `2`            | Retries on failure          |
| `--delay-ms`     | `150`          | Delay between requests (ms) |
| `--max-products` | none           | Cap number of products      |
| `--verbose`      | off            | Print progress details      |

