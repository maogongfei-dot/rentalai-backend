# P3 Phase3: listing_storage 烟测（在 rental_app 下: python test_listing_storage.py）
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from data.schema.listing_schema import ListingSchema
from data.storage.listing_storage import (
    export_listings_as_dicts,
    get_listing_by_id,
    load_listings,
    load_listings_by_source,
    save_listing,
    save_listings,
)


def _tmp() -> str:
    p = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    p.write(b"[]")
    p.close()
    return p.name


def test_single_save_and_load():
    path = _tmp()
    try:
        L = ListingSchema(
            listing_id="a1",
            source="manual",
            rent_pcm=900.0,
            postcode="N1",
        )
        r = save_listing(L, file_path=path)
        assert r["success"] and r["saved"] == 1 and r["updated"] == 0
        loaded = load_listings(file_path=path)
        assert len(loaded) == 1
        assert loaded[0].listing_id == "a1"
        assert loaded[0].rent_pcm == 900.0
    finally:
        Path(path).unlink(missing_ok=True)


def test_dedupe_by_listing_id_updates():
    path = _tmp()
    try:
        save_listing(
            ListingSchema(listing_id="x", source="api", rent_pcm=1000),
            file_path=path,
        )
        r2 = save_listing(
            ListingSchema(listing_id="x", source="api", rent_pcm=1100),
            file_path=path,
        )
        assert r2["updated"] == 1 and r2["saved"] == 0
        assert len(load_listings(file_path=path)) == 1
        assert load_listings(file_path=path)[0].rent_pcm == 1100.0
    finally:
        Path(path).unlink(missing_ok=True)


def test_dedupe_by_url_when_no_id():
    path = _tmp()
    try:
        u = "https://ex.com/1"
        save_listing(
            ListingSchema(source="zoopla", source_url=u, rent_pcm=800),
            file_path=path,
        )
        save_listing(
            ListingSchema(source="zoopla", source_url=u, rent_pcm=850),
            file_path=path,
        )
        assert len(load_listings(file_path=path)) == 1
        assert load_listings(file_path=path)[0].rent_pcm == 850.0
    finally:
        Path(path).unlink(missing_ok=True)


def test_append_when_no_identity():
    path = _tmp()
    try:
        save_listing(ListingSchema(rent_pcm=1, source="manual"), file_path=path)
        save_listing(ListingSchema(rent_pcm=2, source="manual"), file_path=path)
        assert len(load_listings(file_path=path)) == 2
    finally:
        Path(path).unlink(missing_ok=True)


def test_dict_input():
    path = _tmp()
    try:
        save_listing(
            {"listing_id": "d1", "source": "manual", "rent_pcm": 1200},
            file_path=path,
        )
        L = get_listing_by_id("d1", source="manual", file_path=path)
        assert L is not None and L.rent_pcm == 1200.0
    finally:
        Path(path).unlink(missing_ok=True)


def test_batch_and_filter():
    path = _tmp()
    try:
        r = save_listings(
            [
                ListingSchema(listing_id="1", source="api", rent_pcm=100),
                ListingSchema(listing_id="2", source="manual", rent_pcm=200),
                "bad",  # type: ignore[list-item]
            ],
            file_path=path,
        )
        assert r["total"] == 3 and r["skipped"] == 1
        api_only = load_listings_by_source("api", file_path=path)
        assert len(api_only) == 1
        dicts = export_listings_as_dicts(file_path=path)
        assert len(dicts) == 2
    finally:
        Path(path).unlink(missing_ok=True)


def test_missing_file_returns_empty():
    path = str(Path(tempfile.gettempdir()) / "nonexistent_listings_xyz.json")
    Path(path).unlink(missing_ok=True)
    assert load_listings(file_path=path) == []


if __name__ == "__main__":
    test_single_save_and_load()
    test_dedupe_by_listing_id_updates()
    test_dedupe_by_url_when_no_id()
    test_append_when_no_identity()
    test_dict_input()
    test_batch_and_filter()
    test_missing_file_returns_empty()
    print("test_listing_storage: all ok")
