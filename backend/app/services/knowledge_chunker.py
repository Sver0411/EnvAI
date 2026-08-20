from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings


@dataclass(slots=True)
class KnowledgeChunkDraft:
    content: str
    content_type: str = "paragraph"
    section_title: str | None = None
    section_level: int | None = None
    section_path: list[str] = field(default_factory=list)
    article_number: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    table_index: int | None = None
    structured_table: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


_ARTICLE_RE = re.compile(r"^第\s*([零一二三四五六七八九十百千万两0-9]+)\s*条(?:[、.。:]|\s|$)")
_NUM_HEADING_RE = re.compile(r"^(\d+(?:\.\d+){0,5})[\s、.．]+(.+?)\s*$")
_ZH_HEADING_RE = re.compile(r"^(第[一二三四五六七八九十百千万0-9]+章)(?:\s+|、|：)?(.+)?$")


def _estimate_tokens(text: str) -> int:
    # 中文按字符近似，英文/数字按空白词近似；这是索引阶段的估算值。
    return max(1, len(re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+", text)))


def _article_number(line: str) -> str | None:
    match = _ARTICLE_RE.match(line.strip())
    return match.group(1) if match else None


def _heading(line: str) -> tuple[int, str] | None:
    text = line.strip()
    zh = _ZH_HEADING_RE.match(text)
    if zh:
        return 1, " ".join(part for part in (zh.group(1), zh.group(2) or "") if part).strip()
    numeric = _NUM_HEADING_RE.match(text)
    if numeric:
        return numeric.group(1).count(".") + 1, text
    return None


def _split_long(text: str, *, max_tokens: int, overlap_tokens: int) -> list[str]:
    if _estimate_tokens(text) <= max_tokens:
        return [text]
    # 保留段落边界，超长条款才退化为字符窗口。
    pieces: list[str] = []
    paragraphs = [item.strip() for item in re.split(r"\n{2,}", text) if item.strip()]
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip()
        if current and _estimate_tokens(candidate) > max_tokens:
            pieces.append(current)
            tail = current[-overlap_tokens:] if overlap_tokens else ""
            current = f"{tail}\n{paragraph}".strip()
        else:
            current = candidate
    if current:
        pieces.append(current)
    # 单段仍过长时按字符窗口切分。
    final: list[str] = []
    for piece in pieces:
        if _estimate_tokens(piece) <= max_tokens:
            final.append(piece)
            continue
        step = max(1, max_tokens - overlap_tokens)
        for start in range(0, len(piece), step):
            part = piece[start : start + max_tokens]
            if part.strip():
                final.append(part.strip())
    return final


def _page_for_line(pages: list[dict[str, Any]], line_number: int, total_lines: int) -> int | None:
    if not pages:
        return None
    # 解析器页文本没有统一 offset，用比例映射作为保守来源追踪。
    return min(len(pages), max(1, int((line_number / max(total_lines, 1)) * len(pages)) + 1))


def build_knowledge_chunks(structured: dict[str, Any] | None, plain_text: str | None) -> list[KnowledgeChunkDraft]:
    structured = structured or {}
    pages = list(structured.get("pages") or [])
    paragraphs = list(structured.get("paragraphs") or [])
    source_lines: list[tuple[str, dict[str, Any]]] = []
    if paragraphs:
        for item in paragraphs:
            text = str(item.get("text") or "").strip()
            if text:
                source_lines.append((text, item))
    else:
        if pages:
            for page in pages:
                page_number = page.get("page")
                for line in str(page.get("text") or "").splitlines():
                    if line.strip():
                        source_lines.append((line.strip(), {"page": page_number}))
        else:
            for line in (plain_text or "").splitlines():
                if line.strip() and not line.startswith("--- Page ") and not line.startswith("--- Sheet: "):
                    source_lines.append((line.strip(), {}))

    drafts: list[KnowledgeChunkDraft] = []
    section_stack: list[tuple[int, str]] = []
    article_buffer: list[str] = []
    article_number: str | None = None
    article_section: tuple[str | None, int | None, list[str]] = (None, None, [])
    article_page_start: int | None = None
    article_page_end: int | None = None

    def flush_article() -> None:
        nonlocal article_buffer, article_number, article_page_start, article_page_end
        if not article_buffer:
            return
        text = "\n".join(article_buffer).strip()
        for part in _split_long(text, max_tokens=settings.chunk_max_tokens, overlap_tokens=settings.chunk_overlap_tokens):
            drafts.append(KnowledgeChunkDraft(
                content=part,
                content_type="article" if article_number else "paragraph",
                section_title=article_section[0],
                section_level=article_section[1],
                section_path=list(article_section[2]),
                article_number=article_number,
                page_start=article_page_start,
                page_end=article_page_end,
            ))
        article_buffer = []
        article_number = None
        article_page_start = None
        article_page_end = None

    for idx, (line, raw) in enumerate(source_lines):
        heading = _heading(line)
        art = _article_number(line)
        if heading:
            flush_article()
            level, title = heading
            section_stack = [item for item in section_stack if item[0] < level]
            section_stack.append((level, title))
            # 标题自身保留，便于目录/章节检索，但不把空标题写入 chunk。
            drafts.append(KnowledgeChunkDraft(content=title, content_type="section", section_title=title, section_level=level, section_path=[item[1] for item in section_stack], page_start=raw.get("page"), page_end=raw.get("page")))
            continue
        if art:
            flush_article()
            article_number = art
            article_section = (section_stack[-1][1] if section_stack else None, section_stack[-1][0] if section_stack else None, [item[1] for item in section_stack])
            article_page_start = raw.get("page")
            article_page_end = raw.get("page")
            article_buffer.append(line)
            continue
        if article_number:
            article_buffer.append(line)
            if raw.get("page"):
                article_page_end = raw.get("page")
        else:
            for part in _split_long(line, max_tokens=settings.chunk_max_tokens, overlap_tokens=0):
                drafts.append(KnowledgeChunkDraft(content=part, section_title=section_stack[-1][1] if section_stack else None, section_level=section_stack[-1][0] if section_stack else None, section_path=[item[1] for item in section_stack], page_start=raw.get("page"), page_end=raw.get("page")))

    flush_article()

    # 解析器表格结构同时保留可检索纯文本和结构化 headers/rows。
    for table_index, table in enumerate(structured.get("tables") or []):
        rows = table.get("rows") or []
        if not rows:
            continue
        headers = [str(value or "") for value in rows[0]]
        data_rows = [[str(value or "") for value in row] for row in rows[1:]]
        content = "\n".join(" | ".join(row) for row in [headers, *data_rows] if any(row)).strip()
        if content:
            drafts.append(KnowledgeChunkDraft(content=content, content_type="table", table_index=table_index, structured_table={"headers": headers, "rows": data_rows}))

    # 清除完全重复的页眉/目录噪声，并给页码做保守映射。
    unique: list[KnowledgeChunkDraft] = []
    seen: set[str] = set()
    total = len(source_lines)
    for idx, draft in enumerate(drafts):
        draft.content = draft.content.strip()
        if not draft.content:
            continue
        digest = hashlib.sha256(draft.content.encode("utf-8")).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        if draft.page_start is None and pages:
            page = _page_for_line(pages, idx, max(len(drafts), total))
            draft.page_start = page
            draft.page_end = page
        draft.metadata.setdefault("estimated_token_count", _estimate_tokens(draft.content))
        unique.append(draft)
    return unique


def chunk_fingerprint(document_id: int, draft: KnowledgeChunkDraft) -> tuple[str, str, int]:
    normalized = re.sub(r"\s+", " ", draft.content).strip()
    content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    fingerprint = hashlib.sha256(f"{document_id}|{draft.section_path}|{draft.article_number}|{content_hash}".encode()).hexdigest()
    return content_hash, fingerprint, _estimate_tokens(draft.content)
