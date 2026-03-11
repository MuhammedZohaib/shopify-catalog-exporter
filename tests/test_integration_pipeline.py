import csv
import tempfile
import unittest
from pathlib import Path

from shopify_csv_cli.csv_export import write_products_csv
from shopify_csv_cli.extract import extract_product_from_html
from shopify_csv_cli.sitemap import discover_product_urls


class _FakeResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code
        self.encoding = "utf-8"

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeSession:
    def __init__(self, mapping: dict[str, str]) -> None:
        self._mapping = mapping
        self.headers: dict[str, str] = {}

    def get(self, url: str, timeout: float) -> _FakeResponse:
        if url not in self._mapping:
            return _FakeResponse("Not Found", status_code=404)
        return _FakeResponse(self._mapping[url], status_code=200)


class IntegrationPipelineTests(unittest.TestCase):
    def test_end_to_end_pipeline(self) -> None:
        sitemap_index = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap_products_1.xml</loc></sitemap>
</sitemapindex>
"""

        product_sitemap = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/products/a</loc></url>
  <url><loc>https://example.com/products/b</loc></url>
</urlset>
"""

        product_a = """
<html>
  <body>
    <script type="application/json">
      {"handle":"a","title":"A Product","variants":[{"option1":"Default Title","sku":"A1","price":1500}]}
    </script>
  </body>
</html>
"""

        product_b = """
<html>
  <body>
    <script type="application/ld+json">
      {"@context":"https://schema.org","@type":"Product","name":"B Product","offers":{"@type":"Offer","sku":"B1","price":"29.99"}}
    </script>
  </body>
</html>
"""

        mapping = {
            "https://example.com/sitemap.xml": sitemap_index,
            "https://example.com/sitemap_products_1.xml": product_sitemap,
            "https://example.com/products/a": product_a,
            "https://example.com/products/b": product_b,
        }
        session = _FakeSession(mapping)

        product_sitemaps, product_urls = discover_product_urls(
            session=session, domain_or_url="example.com", timeout=5.0, retries=0
        )
        self.assertEqual(len(product_sitemaps), 1)
        self.assertEqual(len(product_urls), 2)

        products = []
        for url in product_urls:
            product = extract_product_from_html(url, mapping[url])
            self.assertIsNotNone(product)
            assert product is not None
            products.append(product)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_products_csv(products, str(Path(tmpdir) / "products.csv"))
            with out_path.open("r", encoding="utf-8-sig", newline="") as fh:
                rows = list(csv.DictReader(fh))

        handles = [row["URL handle"] for row in rows]
        self.assertIn("a", handles)
        self.assertIn("b", handles)


if __name__ == "__main__":
    unittest.main()
