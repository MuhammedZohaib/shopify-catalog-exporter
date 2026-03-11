import csv
import tempfile
import unittest
from pathlib import Path

from shopify_csv_cli.csv_export import load_template_headers, product_to_rows, write_products_csv
from shopify_csv_cli.models import Product, ProductImage, ProductVariant


class CsvExportTests(unittest.TestCase):
    def test_product_to_rows_variants_and_extra_images(self) -> None:
        headers = load_template_headers()
        product = Product(
            handle="sample-product",
            title="Sample Product",
            body_html="<p>Body</p>",
            vendor="Vendor",
            product_category="Apparel & Accessories",
            product_type="Type",
            tags=["a", "b"],
            color_pattern="black",
            option_names=["Size", "Color"],
            variants=[
                ProductVariant(
                    option1="S",
                    option2="Black",
                    sku="SKU1",
                    price="10.00",
                    image_url="https://cdn.shopify.com/variant-1.jpg",
                ),
                ProductVariant(option1="M", option2="Black", sku="SKU2", price="12.00"),
            ],
            images=[
                ProductImage(src="https://cdn.shopify.com/1.jpg", position=1),
                ProductImage(src="https://cdn.shopify.com/2.jpg", position=2),
                ProductImage(src="https://cdn.shopify.com/3.jpg", position=3),
            ],
            seo_title="SEO Title",
            seo_description="SEO Desc",
        )

        rows = product_to_rows(product, headers=headers)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["Title"], "Sample Product")
        self.assertEqual(rows[0]["URL handle"], "sample-product")
        self.assertEqual(rows[0]["SKU"], "SKU1")
        self.assertEqual(rows[0]["Product image URL"], "https://cdn.shopify.com/1.jpg")
        self.assertEqual(rows[0]["Variant image URL"], "https://cdn.shopify.com/variant-1.jpg")
        self.assertEqual(rows[0]["Option2 Linked To"], "product.metafields.shopify.color-pattern")
        self.assertEqual(rows[0]["Color (product.metafields.shopify.color-pattern)"], "black")
        self.assertEqual(rows[1]["Title"], "")
        self.assertEqual(rows[1]["SKU"], "SKU2")
        self.assertEqual(rows[2]["URL handle"], "sample-product")
        self.assertEqual(rows[2]["Product image URL"], "https://cdn.shopify.com/2.jpg")
        self.assertEqual(rows[3]["Product image URL"], "https://cdn.shopify.com/3.jpg")

    def test_write_products_csv(self) -> None:
        product = Product(
            handle="p1",
            title="P1",
            variants=[ProductVariant(option1="Default Title", sku="SKU", price="9.99")],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output = write_products_csv([product], str(Path(tmpdir) / "out.csv"))
            self.assertTrue(output.exists())
            with output.open("r", encoding="utf-8-sig", newline="") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["URL handle"], "p1")
            self.assertEqual(rows[0]["SKU"], "SKU")
            self.assertEqual(rows[0]["Price"], "9.99")


if __name__ == "__main__":
    unittest.main()
