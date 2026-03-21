# P4 Phase5: 轻量布局与状态块（Streamlit），避免页面风格零散
from __future__ import annotations

from typing import Any


def section_header(
    st: Any,
    title: str,
    *,
    level: int = 3,
    caption: str | None = None,
) -> None:
    """统一章节标题层级（level 3 = ###）。"""
    depth = max(2, min(level, 6))
    st.markdown("%s %s" % ("#" * depth, title))
    if caption:
        st.caption(caption)


def card_spacing(st: Any) -> None:
    """卡片之间的轻量竖间距。"""
    st.markdown("")


def state_info(st: Any, message: str) -> None:
    st.info(message)


def state_warning(st: Any, message: str) -> None:
    st.warning(message)


def state_error(st: Any, message: str) -> None:
    st.error(message)
