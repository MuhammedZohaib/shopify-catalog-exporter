import unittest

from shopify_catalog_exporter.sitemap import (
    build_sitemap_index_url,
    filter_product_urls,
    filter_product_sitemaps,
    parse_product_sitemap,
    parse_sitemap_index,
)


SITEMAP_INDEX_XML = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://example.com/sitemap_products_1.xml?from=1&amp;to=2</loc>
  </sitemap>
  <sitemap>
    <loc>https://example.com/sitemap_pages_1.xml</loc>
  </sitemap>
  <sitemap>
    <loc>https://example.com/sitemap_products_2.xml?from=3&amp;to=4</loc>
  </sitemap>
</sitemapindex>
"""


PRODUCT_SITEMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/</loc>
  </url>
  <url>
    <loc>https://example.com/products/alpha-shirt</loc>
  </url>
  <url>
    <loc>https://example.com/products/bravo-shirt</loc>
  </url>
</urlset>
"""


class SitemapTests(unittest.TestCase):
    def test_build_sitemap_index_url_for_domain(self) -> None:
        self.assertEqual(build_sitemap_index_url("example.com"), "https://example.com/sitemap.xml")

    def test_build_sitemap_index_url_for_base_url(self) -> None:
        self.assertEqual(
            build_sitemap_index_url("https://example.com/store"),
            "https://example.com/store/sitemap.xml",
        )

    def test_build_sitemap_index_url_for_explicit_xml(self) -> None:
        self.assertEqual(
            build_sitemap_index_url("https://example.com/custom-sitemap.xml"),
            "https://example.com/custom-sitemap.xml",
        )

    def test_parse_sitemap_index(self) -> None:
        urls = parse_sitemap_index(SITEMAP_INDEX_XML)
        self.assertEqual(len(urls), 3)
        self.assertIn("https://example.com/sitemap_pages_1.xml", urls)

    def test_filter_product_sitemaps(self) -> None:
        all_urls = parse_sitemap_index(SITEMAP_INDEX_XML)
        product_sitemaps = filter_product_sitemaps(all_urls)
        self.assertEqual(len(product_sitemaps), 2)
        self.assertTrue(all("sitemap_products" in url for url in product_sitemaps))

    def test_parse_product_sitemap(self) -> None:
        product_urls = parse_product_sitemap(PRODUCT_SITEMAP_XML)
        self.assertEqual(len(product_urls), 3)

    def test_filter_product_urls(self) -> None:
        product_urls = filter_product_urls(parse_product_sitemap(PRODUCT_SITEMAP_XML))
        self.assertEqual(
            product_urls,
            [
                "https://example.com/products/alpha-shirt",
                "https://example.com/products/bravo-shirt",
            ],
        )


if __name__ == "__main__":
    unittest.main()
