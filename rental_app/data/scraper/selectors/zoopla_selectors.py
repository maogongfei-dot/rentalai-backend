# P7 Phase1：Zoopla 租赁列表页 selector（class 含哈希时用 *= 前缀匹配）
from __future__ import annotations

# 结果列表内的卡片（避免页内其他 listing-card-content）
CARD_ROOT = '[data-testid="regular-listings"] [data-testid="listing-card-content"]'

# 若布局变更导致 regular-listings 缺失时的回退
CARD_ROOT_FALLBACK = '[data-testid="listing-card-content"]'

# 等待列表渲染
CARD_WAIT = '[data-testid="listing-card-content"]'

PRICE_PRIMARY = '[class*="price_priceText"]'
ADDRESS = '[class*="summary_address"]'
SUMMARY = '[class*="summary_summary"]'
