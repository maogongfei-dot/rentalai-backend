# Module3 Phase4-2：条款切分与定位（Clause Segmentation / Locator）
# 在 document_reader 提取的文本基础上，切分为 clause blocks，保留页码、段落、section title 等定位信息。
# 输入为 read_document() 返回的 document_data；输出为统一结构的 block 列表，供后续风险条款识别与缺失条款检测使用。

import re

# 简单规则：可能作为条款/章节标题的关键词（用于 section_title 识别）
SECTION_TITLE_KEYWORDS = (
    "clause", "section", "article", "part",
    "rent", "deposit", "termination", "notice", "repair", "fee",
    "payment", "obligation", "liability", "break", "inventory",
)
# 标题最大长度（字符），超过则不太像标题
SECTION_TITLE_MAX_LEN = 60


def _looks_like_section_title(text: str) -> bool:
    """
    简单启发式：是否像章节/条款标题。
    - 较短且以数字或关键词开头；或全大写；或整行较短且含关键词。
    """
    if not text or not isinstance(text, str):
        return False
    t = text.strip()
    if not t or len(t) > SECTION_TITLE_MAX_LEN:
        return False
    # 以编号开头：1. 2) Clause 3 Section 4 –
    if re.match(r"^[\d]+[\.\)\:\-\s]+", t, re.I):
        return True
    lower = t.lower()
    for kw in SECTION_TITLE_KEYWORDS:
        if lower.startswith(kw) or lower == kw or re.match(rf"^{kw}\s*[\d\.\)\:\-]", lower):
            return True
    # 全大写短句
    if len(t) < 50 and t.isupper() and len(t) > 2:
        return True
    return False


def _next_block_id(block_index: int) -> str:
    """生成唯一 block_id：clause_1, clause_2, ..."""
    return f"clause_{block_index + 1}"


def segment_pdf_blocks(document_data: dict) -> list[dict]:
    """
    将 PDF 文档数据切分为 clause blocks。
    输入 document_data 需含 file_type "pdf" 及 pages_or_sections（每项 {"page": int, "text": str}）。
    按页 + 段落（双换行分隔）切分；段内首行若像标题则识别为 section_title。
    """
    blocks = []
    pages_or_sections = document_data.get("pages_or_sections") or []
    current_section_title = ""
    block_index = 0
    for item in pages_or_sections:
        if not isinstance(item, dict):
            continue
        page = item.get("page")
        if page is None:
            page = 0
        raw = item.get("text") or ""
        paragraphs = re.split(r"\n\s*\n", raw)
        for para in paragraphs:
            para = (para or "").strip()
            if not para:
                continue
            first_line = para.split("\n")[0].strip() if "\n" in para else para
            if _looks_like_section_title(first_line):
                current_section_title = first_line
            blocks.append({
                "block_id": _next_block_id(block_index),
                "page": page,
                "section_title": current_section_title,
                "text": para,
            })
            block_index += 1
    return blocks


def segment_docx_blocks(document_data: dict) -> list[dict]:
    """
    将 DOCX 文档数据切分为 clause blocks。
    输入 document_data 需含 file_type "docx" 及 pages_or_sections（每项 {"index": int, "text": str}）。
    按段落切分，无页码故 page 为 None；对疑似标题的段落识别为 section_title。
    """
    blocks = []
    pages_or_sections = document_data.get("pages_or_sections") or []
    current_section_title = ""
    block_index = 0
    for item in pages_or_sections:
        if not isinstance(item, dict):
            continue
        text = (item.get("text") or "").strip()
        if not text:
            continue
        if _looks_like_section_title(text):
            current_section_title = text
        blocks.append({
            "block_id": _next_block_id(block_index),
            "page": None,
            "section_title": current_section_title,
            "text": text,
        })
        block_index += 1
    return blocks


def build_clause_blocks(document_data: dict) -> list[dict]:
    """
    根据 document_data（read_document 的返回值）自动选择 PDF 或 DOCX 切分逻辑，返回统一 block 列表。
    若存在 error 或 file_type 不支持，返回空列表。
    每个 block: { block_id, page, section_title, text }。
    """
    if not document_data or not isinstance(document_data, dict):
        return []
    if document_data.get("error"):
        return []
    file_type = (document_data.get("file_type") or "").strip().lower()
    if file_type == "pdf":
        return segment_pdf_blocks(document_data)
    if file_type == "docx":
        return segment_docx_blocks(document_data)
    return []
