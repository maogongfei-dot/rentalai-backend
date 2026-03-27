# Phase C5：LLM 预留层（adapter）；当前默认走规则引擎。
from .llm_adapter import (
    LLM_MODE,
    PROMPT_TEMPLATES,
    llm_generate_decision,
    llm_generate_explain,
    llm_parse_query,
)

__all__ = [
    "LLM_MODE",
    "PROMPT_TEMPLATES",
    "llm_generate_decision",
    "llm_generate_explain",
    "llm_parse_query",
]
