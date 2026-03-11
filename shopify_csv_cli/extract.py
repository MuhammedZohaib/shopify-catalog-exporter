from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

from .models import Product, ProductImage, ProductVariant


class _ScriptCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.scripts: list[tuple[str, str]] = []
        self._in_script = False
        self._script_type = ""
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        self._in_script = True
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        self._script_type = attr_dict.get("type", "").lower().strip()
        self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._in_script:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "script" or not self._in_script:
            return
        content = "".join(self._buffer).strip()
        self.scripts.append((self._script_type, content))
        self._in_script = False
        self._script_type = ""
        self._buffer = []


def _handle_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    parts = path.split("/")
    if "products" in parts:
        idx = parts.index("products")
        if idx + 1 < len(parts) and parts[idx + 1]:
            return parts[idx + 1]
    return parts[-1] if parts and parts[-1] else "unknown-product"


def _parse_tags(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(tag).strip() for tag in raw if str(tag).strip()]
    tags = [item.strip() for item in str(raw).split(",")]
    return [tag for tag in tags if tag]


def _absolute_image_url(src: str, base_url: str) -> str:
    src = src.strip()
    if not src:
        return ""
    if src.startswith("//"):
        return f"https:{src}"
    return urljoin(base_url, src)


def _bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return bool(value)


def _to_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_price(raw: Any) -> str:
    if raw is None or raw == "":
        return ""
    if isinstance(raw, bool):
        return ""
    if isinstance(raw, int):
        return f"{Decimal(raw) / Decimal(100):.2f}"
    if isinstance(raw, float):
        return f"{Decimal(str(raw)):.2f}"

    text = str(raw).strip().replace(",", "")
    text = re.sub(r"^[^\d.-]+", "", text)
    if not text:
        return ""
    if re.fullmatch(r"-?\d+", text):
        return f"{Decimal(int(text)) / Decimal(100):.2f}"
    try:
        return f"{Decimal(text):.2f}"
    except (InvalidOperation, ValueError):
        return ""


def _extract_images(data: dict[str, Any], base_url: str) -> list[ProductImage]:
    images: list[ProductImage] = []
    seen: set[str] = set()

    def add_image(raw_src: Any, alt: str = "", position: int | None = None) -> None:
        src = _absolute_image_url(_to_str(raw_src), base_url)
        if not src or src in seen:
            return
        seen.add(src)
        image_position = position if position is not None else (len(images) + 1)
        images.append(ProductImage(src=src, position=image_position, alt_text=alt.strip()))

    raw_images = data.get("images")
    if isinstance(raw_images, list):
        for idx, entry in enumerate(raw_images, start=1):
            if isinstance(entry, dict):
                add_image(
                    entry.get("src") or entry.get("url") or entry.get("originalSrc"),
                    _to_str(entry.get("alt") or entry.get("altText")),
                    idx,
                )
            else:
                add_image(entry, "", idx)

    raw_media = data.get("media")
    if isinstance(raw_media, list):
        for entry in raw_media:
            if not isinstance(entry, dict):
                continue
            preview = entry.get("preview_image")
            add_image(
                entry.get("src")
                or entry.get("url")
                or entry.get("originalSrc")
                or (preview.get("src") if isinstance(preview, dict) else ""),
                _to_str(entry.get("alt") or entry.get("altText")),
            )

    featured = data.get("featured_image") or data.get("image")
    if isinstance(featured, dict):
        add_image(
            featured.get("src") or featured.get("url") or featured.get("originalSrc"),
            _to_str(featured.get("alt") or featured.get("altText")),
        )
    elif featured:
        add_image(featured)

    return images


def _extract_option_names(raw_options: Any) -> list[str]:
    names: list[str] = []
    if isinstance(raw_options, list):
        if raw_options and isinstance(raw_options[0], dict):
            sorted_opts = sorted(raw_options, key=lambda x: int(x.get("position", 999)))
            names = [_to_str(opt.get("name")) for opt in sorted_opts if _to_str(opt.get("name"))]
        else:
            names = [_to_str(opt) for opt in raw_options if _to_str(opt)]

    if not names:
        names = ["Title"]

    return names[:3]


def _extract_variants(raw_variants: Any, option_names: list[str], page_url: str) -> list[ProductVariant]:
    variants: list[ProductVariant] = []
    if isinstance(raw_variants, list):
        for variant in raw_variants:
            if not isinstance(variant, dict):
                continue
            option1 = _to_str(variant.get("option1"))
            option2 = _to_str(variant.get("option2"))
            option3 = _to_str(variant.get("option3"))
            if not option1 and option_names[:1] == ["Title"]:
                option1 = "Default Title"

            variants.append(
                ProductVariant(
                    option1=option1,
                    option2=option2,
                    option3=option3,
                    sku=_to_str(variant.get("sku")),
                    grams=_to_str(variant.get("grams")),
                    inventory_tracker=_to_str(variant.get("inventory_management")),
                    inventory_qty=_to_str(variant.get("inventory_quantity")),
                    inventory_policy=_to_str(variant.get("inventory_policy")) or "deny",
                    fulfillment_service=_to_str(variant.get("fulfillment_service")) or "manual",
                    price=_normalize_price(variant.get("price")),
                    compare_at_price=_normalize_price(variant.get("compare_at_price")),
                    requires_shipping=_bool(variant.get("requires_shipping"), True),
                    taxable=_bool(variant.get("taxable"), True),
                    barcode=_to_str(variant.get("barcode")),
                    image_url=_absolute_image_url(
                        _to_str(
                            variant.get("featured_image", {}).get("src")
                            if isinstance(variant.get("featured_image"), dict)
                            else variant.get("featured_image")
                        )
                        or _to_str(
                            variant.get("image", {}).get("src")
                            if isinstance(variant.get("image"), dict)
                            else variant.get("image")
                        ),
                        page_url,
                    ),
                )
            )

    if not variants:
        option1_default = "Default Title" if option_names[:1] == ["Title"] else ""
        variants = [ProductVariant(option1=option1_default)]

    return variants


def _extract_color_pattern(option_names: list[str], variants: list[ProductVariant]) -> str:
    color_index = -1
    for idx, name in enumerate(option_names[:3]):
        if name.strip().lower() == "color":
            color_index = idx
            break
    if color_index < 0:
        return ""

    colors: set[str] = set()
    for variant in variants:
        value = [variant.option1, variant.option2, variant.option3][color_index].strip()
        if value:
            colors.add(value.lower())
    return "; ".join(sorted(colors))


def _iter_objects(value: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if isinstance(value, dict):
        out.append(value)
        for nested in value.values():
            out.extend(_iter_objects(nested))
    elif isinstance(value, list):
        for item in value:
            out.extend(_iter_objects(item))
    return out


def _looks_like_shopify_product(obj: dict[str, Any]) -> bool:
    title = obj.get("title")
    return isinstance(title, str) and (
        isinstance(obj.get("variants"), list)
        or isinstance(obj.get("options"), list)
        or "handle" in obj
    )


def _load_json_documents(scripts: list[tuple[str, str]], script_type: str) -> list[Any]:
    docs: list[Any] = []
    for candidate_type, content in scripts:
        if candidate_type != script_type or not content:
            continue
        try:
            docs.append(json.loads(content))
        except json.JSONDecodeError:
            continue
    return docs


def _extract_from_shopify_json(docs: list[Any], page_url: str) -> Product | None:
    for doc in docs:
        for obj in _iter_objects(doc):
            if not _looks_like_shopify_product(obj):
                continue
            handle = _to_str(obj.get("handle")) or _handle_from_url(page_url)
            title = _to_str(obj.get("title")) or handle
            option_names = _extract_option_names(obj.get("options"))
            variants = _extract_variants(obj.get("variants"), option_names, page_url)
            taxonomy = obj.get("taxonomy")
            product_category = _to_str(obj.get("category") or obj.get("product_category"))
            if not product_category and isinstance(taxonomy, dict):
                product_category = _to_str(taxonomy.get("full_name"))
            product = Product(
                handle=handle,
                title=title,
                body_html=_to_str(obj.get("body_html") or obj.get("description")),
                vendor=_to_str(obj.get("vendor")),
                product_category=product_category,
                product_type=_to_str(obj.get("product_type") or obj.get("type")),
                tags=_parse_tags(obj.get("tags")),
                published=_bool(obj.get("published"), True),
                option_names=option_names,
                variants=variants,
                images=_extract_images(obj, page_url),
                seo_title=_to_str(
                    (obj.get("seo") or {}).get("title") if isinstance(obj.get("seo"), dict) else ""
                ),
                seo_description=_to_str(
                    (obj.get("seo") or {}).get("description")
                    if isinstance(obj.get("seo"), dict)
                    else ""
                ),
                status=_to_str(obj.get("status")).lower() or "active",
                color_pattern=_extract_color_pattern(option_names, variants),
            )
            product.ensure_defaults()
            return product
    return None


def _is_jsonld_product(obj: dict[str, Any]) -> bool:
    raw_type = obj.get("@type")
    if isinstance(raw_type, list):
        return any(str(item).lower() == "product" for item in raw_type)
    return str(raw_type).lower() == "product"


def _extract_jsonld_product_object(doc: Any) -> dict[str, Any] | None:
    if isinstance(doc, list):
        for item in doc:
            found = _extract_jsonld_product_object(item)
            if found:
                return found
        return None

    if not isinstance(doc, dict):
        return None

    if _is_jsonld_product(doc):
        return doc

    graph = doc.get("@graph")
    if graph:
        found = _extract_jsonld_product_object(graph)
        if found:
            return found

    for value in doc.values():
        found = _extract_jsonld_product_object(value)
        if found:
            return found
    return None


def _variants_from_jsonld_offers(raw_offers: Any) -> list[ProductVariant]:
    offers: list[dict[str, Any]] = []
    if isinstance(raw_offers, dict):
        offers = [raw_offers]
    elif isinstance(raw_offers, list):
        offers = [offer for offer in raw_offers if isinstance(offer, dict)]

    variants: list[ProductVariant] = []
    for offer in offers:
        variants.append(
            ProductVariant(
                option1="Default Title",
                sku=_to_str(offer.get("sku")),
                price=_normalize_price(offer.get("price")),
            )
        )
    return variants


def _extract_from_jsonld(docs: list[Any], page_url: str) -> Product | None:
    for doc in docs:
        product_obj = _extract_jsonld_product_object(doc)
        if not product_obj:
            continue

        brand = product_obj.get("brand")
        vendor = ""
        if isinstance(brand, dict):
            vendor = _to_str(brand.get("name"))
        else:
            vendor = _to_str(brand)

        raw_image = product_obj.get("image")
        images: list[ProductImage] = []
        if isinstance(raw_image, list):
            images = [
                ProductImage(src=_absolute_image_url(_to_str(src), page_url), position=idx + 1)
                for idx, src in enumerate(raw_image)
                if _to_str(src)
            ]
        elif raw_image:
            images = [ProductImage(src=_absolute_image_url(_to_str(raw_image), page_url), position=1)]

        variants = _variants_from_jsonld_offers(product_obj.get("offers"))
        if not variants:
            variants = [ProductVariant(option1="Default Title")]

        title = _to_str(product_obj.get("name")) or _handle_from_url(page_url)
        description = _to_str(product_obj.get("description"))
        product = Product(
            handle=_handle_from_url(page_url),
            title=title,
            body_html=description,
            vendor=vendor,
            product_category=_to_str(product_obj.get("category")),
            product_type=_to_str(product_obj.get("category")),
            tags=[],
            published=True,
            option_names=["Title"],
            variants=variants,
            images=images,
            seo_title=title,
            seo_description=description,
            status="active",
        )
        product.ensure_defaults()
        return product
    return None


def _extract_title_from_html(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    title_text = re.sub(r"\s+", " ", unescape(match.group(1))).strip()
    if " - " in title_text:
        title_text = title_text.split(" - ", 1)[0].strip()
    return title_text


def _extract_meta_content(html: str, attr_name: str, attr_value: str) -> str:
    pattern = (
        rf"<meta[^>]*{attr_name}\s*=\s*['\"]{re.escape(attr_value)}['\"][^>]*content\s*=\s*['\"](.*?)['\"]"
    )
    match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return unescape(match.group(1)).strip()


def _extract_fallback_product(page_url: str, html: str) -> Product | None:
    title = _extract_title_from_html(html) or _handle_from_url(page_url)
    if not title:
        return None

    description = _extract_meta_content(html, "name", "description")
    og_image = _extract_meta_content(html, "property", "og:image")
    images = [ProductImage(src=_absolute_image_url(og_image, page_url), position=1)] if og_image else []

    product = Product(
        handle=_handle_from_url(page_url),
        title=title,
        body_html=description,
        option_names=["Title"],
        variants=[ProductVariant(option1="Default Title")],
        images=images,
        seo_title=title,
        seo_description=description,
    )
    product.ensure_defaults()
    return product


def extract_product_from_html(page_url: str, html: str) -> Product | None:
    parser = _ScriptCollector()
    parser.feed(html)
    scripts = parser.scripts

    product_json_docs = _load_json_documents(scripts, "application/json")
    product = _extract_from_shopify_json(product_json_docs, page_url)
    if product:
        return product

    jsonld_docs = _load_json_documents(scripts, "application/ld+json")
    product = _extract_from_jsonld(jsonld_docs, page_url)
    if product:
        return product

    return _extract_fallback_product(page_url, html)
