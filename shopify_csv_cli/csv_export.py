from __future__ import annotations

import csv
from pathlib import Path

from .models import Product, ProductImage, ProductVariant


DEFAULT_TEMPLATE_HEADERS = [
    "Title",
    "URL handle",
    "Description",
    "Vendor",
    "Product category",
    "Type",
    "Tags",
    "Published on online store",
    "Status",
    "SKU",
    "Barcode",
    "Option1 name",
    "Option1 value",
    "Option1 Linked To",
    "Option2 name",
    "Option2 value",
    "Option2 Linked To",
    "Option3 name",
    "Option3 value",
    "Option3 Linked To",
    "Price",
    "Compare-at price",
    "Cost per item",
    "Charge tax",
    "Tax code",
    "Unit price total measure",
    "Unit price total measure unit",
    "Unit price base measure",
    "Unit price base measure unit",
    "Inventory tracker",
    "Inventory quantity",
    "Continue selling when out of stock",
    "Weight value (grams)",
    "Weight unit for display",
    "Requires shipping",
    "Fulfillment service",
    "Product image URL",
    "Image position",
    "Image alt text",
    "Variant image URL",
    "Gift card",
    "SEO title",
    "SEO description",
    "Color (product.metafields.shopify.color-pattern)",
    "Google Shopping / Google product category",
    "Google Shopping / Gender",
    "Google Shopping / Age group",
    "Google Shopping / Manufacturer part number (MPN)",
    "Google Shopping / Ad group name",
    "Google Shopping / Ads labels",
    "Google Shopping / Condition",
    "Google Shopping / Custom product",
    "Google Shopping / Custom label 0",
    "Google Shopping / Custom label 1",
    "Google Shopping / Custom label 2",
    "Google Shopping / Custom label 3",
    "Google Shopping / Custom label 4",
]


def load_template_headers(template_path: str | None = None) -> list[str]:
    candidates: list[Path] = []
    if template_path:
        candidates.append(Path(template_path).expanduser())
    candidates.append(Path.cwd() / "product_template.csv")
    candidates.append(Path(__file__).resolve().parent.parent / "product_template.csv")

    for candidate in candidates:
        if not candidate.exists():
            continue
        with candidate.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.reader(fh)
            header = next(reader, [])
        if header:
            return header
    return DEFAULT_TEMPLATE_HEADERS[:]


def _bool_str(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def _status_str(value: str) -> str:
    lowered = value.strip().lower()
    if lowered == "active":
        return "Active"
    if lowered == "draft":
        return "Draft"
    if lowered == "archived":
        return "Archived"
    return value.strip() or "Active"


def _inventory_policy_str(value: str) -> str:
    lowered = value.strip().lower()
    if lowered == "continue":
        return "CONTINUE"
    return "DENY"


def _blank_row(headers: list[str]) -> dict[str, str]:
    return {header: "" for header in headers}


def _normalized_option_names(option_names: list[str]) -> tuple[str, str, str]:
    names = option_names[:3]
    while len(names) < 3:
        names.append("")
    return names[0], names[1], names[2]


def _linked_to(option_name: str) -> str:
    if option_name.strip().lower() == "color":
        return "product.metafields.shopify.color-pattern"
    return ""


def _variant_to_row_base(
    headers: list[str], product: Product, variant: ProductVariant, option_names: tuple[str, str, str]
) -> dict[str, str]:
    option1_name, option2_name, option3_name = option_names
    option1_value = variant.option1
    if not option1_value and option1_name == "Title":
        option1_value = "Default Title"

    row = _blank_row(headers)
    row["URL handle"] = product.handle
    row["SKU"] = variant.sku
    row["Barcode"] = variant.barcode
    row["Option1 name"] = option1_name
    row["Option1 value"] = option1_value
    row["Option1 Linked To"] = _linked_to(option1_name)
    row["Option2 name"] = option2_name
    row["Option2 value"] = variant.option2
    row["Option2 Linked To"] = _linked_to(option2_name)
    row["Option3 name"] = option3_name
    row["Option3 value"] = variant.option3
    row["Option3 Linked To"] = _linked_to(option3_name)
    row["Price"] = variant.price
    row["Compare-at price"] = variant.compare_at_price
    row["Charge tax"] = _bool_str(variant.taxable)
    row["Inventory tracker"] = variant.inventory_tracker
    row["Inventory quantity"] = variant.inventory_qty
    row["Continue selling when out of stock"] = _inventory_policy_str(variant.inventory_policy)
    row["Weight value (grams)"] = variant.grams
    row["Weight unit for display"] = "g" if variant.grams else ""
    row["Requires shipping"] = _bool_str(variant.requires_shipping)
    row["Fulfillment service"] = variant.fulfillment_service
    row["Variant image URL"] = variant.image_url
    row["Google Shopping / Manufacturer part number (MPN)"] = variant.sku
    return row


def _apply_product_fields(
    row: dict[str, str], product: Product, image: ProductImage | None = None
) -> None:
    row["Title"] = product.title
    row["Description"] = product.body_html
    row["Vendor"] = product.vendor
    row["Product category"] = product.product_category
    row["Type"] = product.product_type
    row["Tags"] = ", ".join(product.tags)
    row["Published on online store"] = _bool_str(product.published)
    row["Status"] = _status_str(product.status)
    row["Gift card"] = _bool_str(product.gift_card)
    row["SEO title"] = product.seo_title
    row["SEO description"] = product.seo_description
    row["Color (product.metafields.shopify.color-pattern)"] = product.color_pattern
    if image:
        row["Product image URL"] = image.src
        row["Image position"] = str(image.position)
        row["Image alt text"] = image.alt_text


def product_to_rows(product: Product, headers: list[str] | None = None) -> list[dict[str, str]]:
    product.ensure_defaults()
    active_headers = headers or DEFAULT_TEMPLATE_HEADERS
    option_names = _normalized_option_names(product.option_names)

    rows: list[dict[str, str]] = []
    primary_image = product.images[0] if product.images else None

    for idx, variant in enumerate(product.variants):
        row = _variant_to_row_base(active_headers, product, variant, option_names)
        if idx == 0:
            _apply_product_fields(row, product, image=primary_image)
        rows.append(row)

    for image in product.images[1:]:
        row = _blank_row(active_headers)
        row["URL handle"] = product.handle
        row["Product image URL"] = image.src
        row["Image position"] = str(image.position)
        row["Image alt text"] = image.alt_text
        rows.append(row)

    return rows


def write_products_csv(
    products: list[Product], output_path: str, template_path: str | None = None
) -> Path:
    headers = load_template_headers(template_path)
    out_path = Path(output_path).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for product in products:
            for row in product_to_rows(product, headers=headers):
                writer.writerow(row)

    return out_path
