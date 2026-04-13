from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ProductImage:
    src: str
    position: int = 1
    alt_text: str = ""


@dataclass(slots=True)
class ProductVariant:
    option1: str = ""
    option2: str = ""
    option3: str = ""
    sku: str = ""
    grams: str = ""
    inventory_tracker: str = ""
    inventory_qty: str = ""
    inventory_policy: str = "deny"
    fulfillment_service: str = "manual"
    price: str = ""
    compare_at_price: str = ""
    requires_shipping: bool = True
    taxable: bool = True
    barcode: str = ""
    image_url: str = ""


@dataclass(slots=True)
class Product:
    handle: str
    title: str
    body_html: str = ""
    vendor: str = ""
    product_category: str = ""
    product_type: str = ""
    tags: list[str] = field(default_factory=list)
    published: bool = True
    option_names: list[str] = field(default_factory=list)
    variants: list[ProductVariant] = field(default_factory=list)
    images: list[ProductImage] = field(default_factory=list)
    gift_card: bool = False
    seo_title: str = ""
    seo_description: str = ""
    status: str = "active"
    color_pattern: str = ""

    def ensure_defaults(self) -> None:
        if not self.option_names:
            self.option_names = ["Title"]
        if not self.variants:
            self.variants = [ProductVariant(option1="Default Title")]
