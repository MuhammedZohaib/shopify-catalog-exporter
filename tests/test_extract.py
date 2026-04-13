import unittest

from shopify_catalog_exporter.extract import (
    build_product_json_url,
    extract_product_from_html,
    extract_product_from_json_text,
)


HTML_WITH_PRODUCT_JSON = """
<html>
  <head><title>Test Shirt - My Store</title></head>
  <body>
    <script type="application/json">
      {
        "id": 123,
        "handle": "test-shirt",
        "title": "Test Shirt",
        "body_html": "<p>Soft cotton</p>",
        "vendor": "Acme",
        "product_type": "Shirts",
        "tags": ["summer", "cotton"],
        "options": [{"name":"Size","position":1}, {"name":"Color","position":2}],
        "variants": [{
          "sku": "SKU-S-BLK",
          "price": 2599,
          "compare_at_price": 3099,
          "option1": "Small",
          "option2": "Black",
          "inventory_management": "shopify",
          "inventory_quantity": 5,
          "inventory_policy": "deny",
          "fulfillment_service": "manual",
          "grams": 200,
          "requires_shipping": true,
          "taxable": true,
          "barcode": "111",
          "featured_image": {"src": "/cdn/shop/files/variant-black.jpg"}
        }],
        "images": ["//cdn.shopify.com/a.jpg", "https://cdn.shopify.com/b.jpg"],
        "media": [{"preview_image": {"src": "https://cdn.shopify.com/c.jpg"}}]
      }
    </script>
  </body>
</html>
"""


HTML_WITH_JSONLD = """
<html>
  <head>
    <script type="application/ld+json">
      {
        "@context":"https://schema.org",
        "@type":"Product",
        "name":"JSON-LD Product",
        "description":"A product from JSON-LD",
        "brand":{"@type":"Brand","name":"BrandCo"},
        "image":["https://cdn.shopify.com/jsonld.jpg"],
        "offers":[{"@type":"Offer","price":"19.99","sku":"LD-1"}]
      }
    </script>
  </head>
  <body></body>
</html>
"""


HTML_FALLBACK = """
<html>
  <head>
    <title>Fallback Product - Demo Store</title>
    <meta name="description" content="Fallback desc">
    <meta property="og:image" content="//cdn.shopify.com/fallback.jpg">
  </head>
  <body></body>
</html>
"""


class ExtractTests(unittest.TestCase):
    def test_build_product_json_url(self) -> None:
        self.assertEqual(
            build_product_json_url("https://example.com/products/test-shirt?variant=1"),
            "https://example.com/products/test-shirt.js",
        )

    def test_extract_from_shopify_product_json(self) -> None:
        product = extract_product_from_html(
            "https://example.com/products/test-shirt", HTML_WITH_PRODUCT_JSON
        )
        self.assertIsNotNone(product)
        assert product is not None
        self.assertEqual(product.handle, "test-shirt")
        self.assertEqual(product.title, "Test Shirt")
        self.assertEqual(product.vendor, "Acme")
        self.assertEqual(product.product_type, "Shirts")
        self.assertEqual(product.tags, ["summer", "cotton"])
        self.assertEqual(product.option_names, ["Size", "Color"])
        self.assertEqual(product.color_pattern, "black")
        self.assertEqual(len(product.variants), 1)
        self.assertEqual(product.variants[0].price, "25.99")
        self.assertEqual(product.variants[0].compare_at_price, "30.99")
        self.assertEqual(
            product.variants[0].image_url,
            "https://example.com/cdn/shop/files/variant-black.jpg",
        )
        self.assertEqual(product.images[0].src, "https://cdn.shopify.com/a.jpg")
        self.assertEqual(product.images[1].src, "https://cdn.shopify.com/b.jpg")
        self.assertEqual(product.images[2].src, "https://cdn.shopify.com/c.jpg")

    def test_extract_from_storefront_json_text(self) -> None:
        json_text = """
        {
          "id": 1,
          "title": "Direct Product",
          "handle": "direct-product",
          "vendor": "Acme",
          "product_type": "Shoes",
          "tags": "shoe, leather",
          "options": ["Title"],
          "variants": [
            {"id": 11, "title": "Default Title", "option1": "Default Title", "sku": "D1", "price": 1000}
          ],
          "images": ["https://cdn.shopify.com/direct.jpg"]
        }
        """
        product = extract_product_from_json_text(
            "https://example.com/products/direct-product",
            json_text,
        )
        self.assertIsNotNone(product)
        assert product is not None
        self.assertEqual(product.handle, "direct-product")
        self.assertEqual(product.variants[0].option1, "Default Title")
        self.assertEqual(product.images[0].src, "https://cdn.shopify.com/direct.jpg")

    def test_unavailable_variant_without_quantity_forces_zero_qty(self) -> None:
        json_text = """
        {
          "id": 1,
          "title": "Stock Product",
          "handle": "stock-product",
          "options": ["Title"],
          "variants": [
            {"id": 11, "title": "Default Title", "option1": "Default Title", "available": false, "price": 1000}
          ]
        }
        """
        product = extract_product_from_json_text(
            "https://example.com/products/stock-product",
            json_text,
        )
        self.assertIsNotNone(product)
        assert product is not None
        self.assertEqual(product.variants[0].inventory_qty, "0")

    def test_extract_from_jsonld(self) -> None:
        product = extract_product_from_html(
            "https://example.com/products/jsonld-product", HTML_WITH_JSONLD
        )
        self.assertIsNotNone(product)
        assert product is not None
        self.assertEqual(product.title, "JSON-LD Product")
        self.assertEqual(product.vendor, "BrandCo")
        self.assertEqual(len(product.variants), 1)
        self.assertEqual(product.variants[0].price, "19.99")
        self.assertEqual(product.variants[0].sku, "LD-1")
        self.assertEqual(product.images[0].src, "https://cdn.shopify.com/jsonld.jpg")

    def test_extract_fallback_when_json_missing(self) -> None:
        product = extract_product_from_html(
            "https://example.com/products/fallback-item", HTML_FALLBACK
        )
        self.assertIsNotNone(product)
        assert product is not None
        self.assertEqual(product.handle, "fallback-item")
        self.assertEqual(product.title, "Fallback Product")
        self.assertEqual(product.seo_description, "Fallback desc")
        self.assertEqual(product.images[0].src, "https://cdn.shopify.com/fallback.jpg")


if __name__ == "__main__":
    unittest.main()
