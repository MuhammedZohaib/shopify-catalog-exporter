from __future__ import annotations

from urllib.parse import urlparse
from xml.etree import ElementTree as ET

from .http_utils import fetch_text
from .http_utils import SessionLike


def build_sitemap_index_url(domain_or_url: str) -> str:
    raw = domain_or_url.strip()
    if not raw:
        raise ValueError("Domain or URL cannot be empty.")

    if "://" not in raw:
        raw = f"https://{raw}"

    parsed = urlparse(raw)
    if not parsed.netloc:
        raise ValueError(f"Invalid domain or URL: {domain_or_url}")

    path = parsed.path or ""
    if not path or path == "/":
        path = "/sitemap.xml"
    elif not path.endswith(".xml"):
        path = f"{path.rstrip('/')}/sitemap.xml"

    return f"{parsed.scheme}://{parsed.netloc}{path}"


def parse_sitemap_index(xml_text: str) -> list[str]:
    root = ET.fromstring(xml_text)
    urls: list[str] = []
    for sitemap_elem in root.iter():
        if not sitemap_elem.tag.endswith("sitemap"):
            continue
        for child in sitemap_elem:
            if child.tag.endswith("loc") and child.text:
                urls.append(child.text.strip())
    return urls


def parse_product_sitemap(xml_text: str) -> list[str]:
    root = ET.fromstring(xml_text)
    product_urls: list[str] = []
    for url_elem in root.iter():
        if not url_elem.tag.endswith("url"):
            continue
        for child in url_elem:
            if child.tag.endswith("loc") and child.text:
                product_urls.append(child.text.strip())
    return product_urls


def filter_product_sitemaps(sitemap_urls: list[str]) -> list[str]:
    return [url for url in sitemap_urls if "sitemap_products" in url.lower()]


def filter_product_urls(urls: list[str]) -> list[str]:
    filtered: list[str] = []
    for url in urls:
        path = urlparse(url).path.lower()
        if "/products/" in path:
            filtered.append(url)
    return filtered


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def discover_product_urls(
    session: SessionLike,
    domain_or_url: str,
    timeout: float,
    retries: int,
    verbose: bool = False,
) -> tuple[list[str], list[str]]:
    index_url = build_sitemap_index_url(domain_or_url)
    if verbose:
        print(f"Discovering sitemaps from {index_url}")
    index_xml = fetch_text(session, index_url, timeout=timeout, retries=retries, verbose=verbose)

    all_sitemaps = parse_sitemap_index(index_xml)
    product_sitemaps = filter_product_sitemaps(all_sitemaps)
    product_sitemaps = _dedupe_keep_order(product_sitemaps)

    all_product_urls: list[str] = []
    for sitemap_url in product_sitemaps:
        sitemap_xml = fetch_text(
            session, sitemap_url, timeout=timeout, retries=retries, verbose=verbose
        )
        all_product_urls.extend(filter_product_urls(parse_product_sitemap(sitemap_xml)))

    all_product_urls = _dedupe_keep_order(all_product_urls)
    return product_sitemaps, all_product_urls
