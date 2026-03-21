# P3 Phase3: 标准房源本地 JSON 持久化（无 DB / 无 scraper）
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from data.schema.listing_schema import ListingSchema

# 与 schema、normalizer 同级：rental_app/data/listings.json
_DATA_DIR = Path(__file__).resolve().parent.parent
_env_listings = (os.environ.get("RENTALAI_LISTINGS_PATH") or "").strip()
if _env_listings:
    DEFAULT_LISTINGS_PATH = str(Path(_env_listings).expanduser().resolve())
else:
    DEFAULT_LISTINGS_PATH = str(_DATA_DIR / "listings.json")


def _resolve_path(file_path: str | None) -> Path:
    return Path(file_path or DEFAULT_LISTINGS_PATH).expanduser().resolve()


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _read_json_file(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            return []
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        return [x for x in data if isinstance(x, dict)]
    except (OSError, json.JSONDecodeError, TypeError):
        return []


def _write_json_file(path: Path, rows: list[dict[str, Any]]) -> None:
    _ensure_parent(path)
    path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _coerce_listing(item: ListingSchema | dict) -> ListingSchema:
    if isinstance(item, ListingSchema):
        return item
    if isinstance(item, dict):
        return ListingSchema.from_dict(item)
    raise TypeError("listing must be ListingSchema or dict")


def _norm_source(s: Any) -> str:
    if isinstance(s, str) and s.strip():
        return s.strip().lower()
    return "unknown"


def _identity_from_row(row: dict[str, Any]) -> tuple[str, str, str] | None:
    """与 ListingSchema 行一致的去重键；无键则 None。"""
    src = _norm_source(row.get("source"))
    lid = row.get("listing_id")
    if lid is not None and str(lid).strip():
        return ("id", src, str(lid).strip())
    url = row.get("source_url")
    if url is not None and str(url).strip():
        return ("url", src, str(url).strip())
    return None


def _identity_key(listing: ListingSchema) -> tuple[str, str, str] | None:
    src = _norm_source(listing.source)
    if listing.listing_id and str(listing.listing_id).strip():
        return ("id", src, str(listing.listing_id).strip())
    if listing.source_url and str(listing.source_url).strip():
        return ("url", src, str(listing.source_url).strip())
    return None


def _listing_to_storage_dict(listing: ListingSchema) -> dict[str, Any]:
    return listing.to_dict()


def _upsert_one(rows: list[dict[str, Any]], listing: ListingSchema) -> str:
    """
    在内存列表中插入或覆盖；返回 'saved' | 'updated'。
    无 identity 时总是追加。
    """
    payload = _listing_to_storage_dict(listing)
    key = _identity_key(listing)
    if key is None:
        rows.append(payload)
        return "saved"
    for i, row in enumerate(rows):
        if _identity_from_row(row) == key:
            rows[i] = payload
            return "updated"
    rows.append(payload)
    return "saved"


def save_listings(
    listings: list[ListingSchema | dict],
    file_path: str | None = None,
) -> dict[str, Any]:
    """
    批量保存；单条失败计入 skipped，不拖垮整批。
    返回 saved / updated / skipped / total。
    """
    path = _resolve_path(file_path)
    rows = _read_json_file(path)
    saved = updated = skipped = 0
    total = len(listings) if isinstance(listings, list) else 0
    if not isinstance(listings, list):
        return {
            "success": False,
            "saved": 0,
            "updated": 0,
            "skipped": 0,
            "total": 0,
        }
    for item in listings:
        try:
            L = _coerce_listing(item)
            op = _upsert_one(rows, L)
            if op == "saved":
                saved += 1
            else:
                updated += 1
        except Exception:
            skipped += 1
    try:
        _write_json_file(path, rows)
    except OSError:
        return {
            "success": False,
            "saved": 0,
            "updated": 0,
            "skipped": total,
            "total": total,
        }
    return {
        "success": True,
        "saved": saved,
        "updated": updated,
        "skipped": skipped,
        "total": total,
    }


def save_listing(
    listing: ListingSchema | dict,
    file_path: str | None = None,
) -> dict[str, Any]:
    """单条保存；dict 会先经 ListingSchema.from_dict。"""
    r = save_listings([listing], file_path=file_path)
    return {
        "success": r["success"],
        "saved": r["saved"],
        "updated": r["updated"],
    }


def load_listings(file_path: str | None = None) -> list[ListingSchema]:
    """读取全部；坏项跳过。"""
    path = _resolve_path(file_path)
    rows = _read_json_file(path)
    out: list[ListingSchema] = []
    for row in rows:
        try:
            out.append(ListingSchema.from_dict(row))
        except Exception:
            continue
    return out


def load_listings_by_source(
    source: str,
    file_path: str | None = None,
) -> list[ListingSchema]:
    want = _norm_source(source)
    return [L for L in load_listings(file_path) if _norm_source(L.source) == want]


def get_listing_by_id(
    listing_id: str,
    source: str | None = None,
    file_path: str | None = None,
) -> ListingSchema | None:
    lid = str(listing_id).strip()
    if not lid:
        return None
    src_filter = _norm_source(source) if source else None
    for L in load_listings(file_path):
        if not L.listing_id or str(L.listing_id).strip() != lid:
            continue
        if src_filter is not None and _norm_source(L.source) != src_filter:
            continue
        return L
    return None


def export_listings_as_dicts(file_path: str | None = None) -> list[dict[str, Any]]:
    """便于 API / 调试的纯 dict 列表。"""
    return [L.to_dict() for L in load_listings(file_path)]


# 最小使用示例（README 亦有说明）
if __name__ == "__main__":
    import tempfile

    p = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    Path(p).write_text("[]", encoding="utf-8")
    L = ListingSchema(
        listing_id="t1",
        source="manual",
        rent_pcm=1000.0,
        postcode="E1",
    )
    print(save_listing(L, file_path=p))
    print(load_listings(file_path=p)[0].rent_pcm)
