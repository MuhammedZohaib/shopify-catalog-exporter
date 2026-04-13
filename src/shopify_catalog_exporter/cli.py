from __future__ import annotations

import argparse
import sys
import time

from .csv_export import write_products_csv
from .extract import build_product_json_url, extract_product_from_html, extract_product_from_json_text
from .http_utils import DEFAULT_USER_AGENT, create_session, fetch_text
from .sitemap import discover_product_urls


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shopify-products-to-csv",
        description="Discover Shopify products from sitemap and export import-ready CSV.",
    )
    parser.add_argument("store", help="Shopify domain, base URL, or sitemap XML URL.")
    parser.add_argument(
        "--output",
        default="products.csv",
        help="Output CSV file path (default: products.csv).",
    )
    parser.add_argument(
        "--template",
        default=None,
        help="Optional CSV template path. Defaults to product_template.csv when present.",
    )
    parser.add_argument(
        "--timeout", type=float, default=10.0, help="HTTP timeout in seconds (default: 10)."
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="HTTP retries for failed requests (default: 2).",
    )
    parser.add_argument(
        "--delay-ms",
        type=int,
        default=150,
        help="Delay between product requests in milliseconds (default: 150).",
    )
    parser.add_argument(
        "--max-products",
        type=int,
        default=None,
        help="Optional limit for number of products to process.",
    )
    parser.add_argument("--verbose", action="store_true", help="Print progress details.")
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.retries < 0:
        print("--retries must be >= 0", file=sys.stderr)
        return 2
    if args.timeout <= 0:
        print("--timeout must be > 0", file=sys.stderr)
        return 2
    if args.delay_ms < 0:
        print("--delay-ms must be >= 0", file=sys.stderr)
        return 2
    if args.max_products is not None and args.max_products <= 0:
        print("--max-products must be > 0 when provided", file=sys.stderr)
        return 2

    session = create_session()
    session.headers.update({"User-Agent": DEFAULT_USER_AGENT})

    try:
        product_sitemaps, product_urls = discover_product_urls(
            session=session,
            domain_or_url=args.store,
            timeout=args.timeout,
            retries=args.retries,
            verbose=args.verbose,
        )
    except Exception as exc:
        print(f"Failed to discover product sitemap URLs: {exc}", file=sys.stderr)
        return 2

    if not product_sitemaps:
        print("No product sitemap files found.", file=sys.stderr)
        return 1
    if not product_urls:
        print("No product URLs found in product sitemap files.", file=sys.stderr)
        return 1

    if args.max_products is not None:
        product_urls = product_urls[: args.max_products]

    if args.verbose:
        print(f"Product sitemaps discovered: {len(product_sitemaps)}")
        print(f"Product URLs discovered: {len(product_urls)}")

    products = []
    failures: list[tuple[str, str]] = []
    total = len(product_urls)
    for idx, product_url in enumerate(product_urls, start=1):
        if args.verbose:
            print(f"[{idx}/{total}] Scraping {product_url}")
        try:
            product = None

            product_json_url = build_product_json_url(product_url)
            try:
                product_json = fetch_text(
                    session=session,
                    url=product_json_url,
                    timeout=args.timeout,
                    retries=args.retries,
                    verbose=False,
                )
                product = extract_product_from_json_text(product_url, product_json)
            except Exception:
                product = None

            if product is None:
                html = fetch_text(
                    session=session,
                    url=product_url,
                    timeout=args.timeout,
                    retries=args.retries,
                    verbose=args.verbose,
                )
                product = extract_product_from_html(product_url, html)

            if product is None:
                failures.append((product_url, "Unable to parse product details"))
            else:
                products.append(product)
        except Exception as exc:
            failures.append((product_url, str(exc)))

        if idx < total and args.delay_ms:
            time.sleep(args.delay_ms / 1000.0)

    if not products:
        print("No products could be exported.", file=sys.stderr)
        if failures and args.verbose:
            for url, reason in failures:
                print(f"FAIL {url} -> {reason}", file=sys.stderr)
        return 1

    output_path = write_products_csv(products, args.output, template_path=args.template)
    print(f"CSV written to: {output_path}")
    print(
        f"Summary: sitemaps={len(product_sitemaps)}, urls={len(product_urls)}, "
        f"exported={len(products)}, failed={len(failures)}"
    )
    if failures:
        print("Failed product URLs:")
        for url, reason in failures[:10]:
            print(f"- {url} -> {reason}")
        if len(failures) > 10:
            print(f"... and {len(failures) - 10} more")

    return 0


def main() -> None:
    raise SystemExit(run())
