# P6 Phase5：Zoopla pipeline 占位结构（在 rental_app 下: python test_zoopla_pipeline.py）
from __future__ import annotations

from data.pipeline.zoopla_pipeline import run_zoopla_pipeline


def test_run_zoopla_pipeline_placeholder_shape():
    r = run_zoopla_pipeline()
    assert r.get("success") is False
    assert r.get("error")
    for k in (
        "raw_count",
        "normalized_count",
        "normalization_skipped",
        "saved",
        "updated",
        "skipped",
    ):
        assert k in r
        assert r[k] == 0


if __name__ == "__main__":
    test_run_zoopla_pipeline_placeholder_shape()
    print("test_zoopla_pipeline: all ok")
