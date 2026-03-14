# Module3 Phase4-1：Document 读取入口（PDF / Word 文本提取）
# 接收用户上传的合同文件，提取可分析文本，为后续条款定位、风险识别、缺失条款检测做准备。
# 依赖：pypdf（PDF）、python-docx（DOCX）。安装：pip install pypdf python-docx

import os


def extract_text_from_pdf(file_path: str) -> dict:
    """
    从 PDF 文件提取文本。
    返回: { file_name, file_type, full_text, pages_or_sections }；
    pages_or_sections 为按页的文本列表，每项为 {"page": 页码(1-based), "text": "该页文本"}。
    若缺少 pypdf 或文件异常，返回结构中含 "error" 键。
    """
    file_name = os.path.basename(file_path)
    result = {
        "file_name": file_name,
        "file_type": "pdf",
        "full_text": "",
        "pages_or_sections": [],
    }
    try:
        from pypdf import PdfReader
    except ImportError:
        result["error"] = "pypdf not installed. Run: pip install pypdf"
        return result

    if not os.path.isfile(file_path):
        result["error"] = f"File not found: {file_path}"
        return result

    try:
        reader = PdfReader(file_path)
        pages = reader.pages
        page_texts = []
        full_parts = []
        for i, page in enumerate(pages):
            text = (page.extract_text() or "").strip()
            page_texts.append({"page": i + 1, "text": text})
            full_parts.append(text)
        result["pages_or_sections"] = page_texts
        result["full_text"] = "\n\n".join(full_parts)
    except Exception as e:
        result["error"] = str(e)
    return result


def extract_text_from_docx(file_path: str) -> dict:
    """
    从 DOCX 文件提取文本（按段落）。
    返回: { file_name, file_type, full_text, pages_or_sections }；
    pages_or_sections 为按段落的文本列表，每项为 {"index": 序号, "text": "该段文本"}。
    DOCX 无“页”概念，此处用段落作为可定位单元。
    若缺少 python-docx 或文件异常，返回结构中含 "error" 键。
    """
    file_name = os.path.basename(file_path)
    result = {
        "file_name": file_name,
        "file_type": "docx",
        "full_text": "",
        "pages_or_sections": [],
    }
    try:
        from docx import Document
    except ImportError:
        result["error"] = "python-docx not installed. Run: pip install python-docx"
        return result

    if not os.path.isfile(file_path):
        result["error"] = f"File not found: {file_path}"
        return result

    try:
        doc = Document(file_path)
        parts = []
        for idx, para in enumerate(doc.paragraphs):
            text = (para.text or "").strip()
            parts.append({"index": idx + 1, "text": text})
        texts_only = [p["text"] for p in parts]
        result["pages_or_sections"] = parts
        result["full_text"] = "\n\n".join(texts_only)
    except Exception as e:
        result["error"] = str(e)
    return result


def read_document(file_path: str) -> dict:
    """
    根据文件扩展名自动选择 PDF 或 DOCX 提取器，返回统一结构：
    { file_name, file_type, full_text, pages_or_sections }；
    不支持的类型或缺失扩展名时返回含 "error" 的同样结构。
    """
    if not file_path or not isinstance(file_path, str):
        return {
            "file_name": "",
            "file_type": "",
            "full_text": "",
            "pages_or_sections": [],
            "error": "Invalid file_path",
        }
    path_lower = file_path.lower().strip()
    if path_lower.endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    if path_lower.endswith(".docx"):
        return extract_text_from_docx(file_path)
    return {
        "file_name": os.path.basename(file_path),
        "file_type": "",
        "full_text": "",
        "pages_or_sections": [],
        "error": "Unsupported file type. Use .pdf or .docx",
    }
