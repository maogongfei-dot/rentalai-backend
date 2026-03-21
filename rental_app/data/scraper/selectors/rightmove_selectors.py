# P6 Phase3：Rightmove 列表页关键 selector（部分 class 含哈希后缀，用 *= 匹配稳定前缀）
from __future__ import annotations

# 单张卡片根节点（当前页 ~50 条）
CARD_ROOT = '[data-testid^="propertyCard-"]'

# 详情链接（同卡内多条重复，取 href 即可）
LINK_PROPERTY = 'a[href^="/properties/"]'

# 价格主行（pcm）；次级 pw 在同一块内，本阶段只取主行
PRICE_PRIMARY = '[class*="PropertyPrice_price__"]'

# 地址与标题区
ADDRESS = '[class*="PropertyAddress_address__"]'
TITLE_BLOCK = '[class*="PropertyCardTitle_container"]'

# 描述摘要
SUMMARY = '[class*="PropertyCardSummary_summary"]'

# 房型 / 卧室数（文本块）
PROPERTY_TYPE = '[class*="PropertyInformation_propertyType"]'
BEDROOMS_COUNT = '[class*="PropertyInformation_bedroomsCount"]'
