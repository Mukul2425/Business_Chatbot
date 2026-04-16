"""
Local knowledge base service for business documents.

Supports markdown, text, and Word documents stored in data/knowledge_base.
Uses semantic search for retrieval and can provide snippets for Gemini context.
"""
import os
import re

import numpy as np

try:
    from docx import Document
except Exception:  # pragma: no cover - optional dependency handling
    Document = None

from app.services.semantic_service import model


KNOWLEDGE_BASE_DIR = os.path.join("data", "knowledge_base")
SUPPORTED_EXTENSIONS = {".md", ".txt", ".docx"}

_kb_cache_signature = None
_kb_chunks_cache = []
_kb_embeddings_cache = None


def _list_knowledge_files():
    if not os.path.isdir(KNOWLEDGE_BASE_DIR):
        return []

    files = []
    for entry in os.listdir(KNOWLEDGE_BASE_DIR):
        path = os.path.join(KNOWLEDGE_BASE_DIR, entry)
        if os.path.isfile(path) and os.path.splitext(path)[1].lower() in SUPPORTED_EXTENSIONS:
            files.append(path)
    return sorted(files)


def _build_signature(files):
    parts = []
    for path in files:
        stat = os.stat(path)
        parts.append(f"{path}:{stat.st_mtime_ns}:{stat.st_size}")
    return "|".join(parts)


def _read_docx(path):
    if Document is None:
        return ""

    try:
        doc = Document(path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
        return "\n\n".join(paragraphs)
    except Exception:
        # Do not break the bot for one unreadable/corrupted doc file.
        return ""


def _read_text_file(path):
    try:
        with open(path, "r", encoding="utf-8") as file_handle:
            return file_handle.read().strip()
    except Exception:
        return ""


def _read_file_text(path):
    extension = os.path.splitext(path)[1].lower()
    if extension in {".txt", ".md"}:
        return _read_text_file(path)
    if extension == ".docx":
        return _read_docx(path)
    return ""


def _split_into_chunks(text, max_chars=800):
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        return []

    chunks = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            start = 0
            while start < len(paragraph):
                chunks.append(paragraph[start:start + max_chars].strip())
                start += max_chars
            continue

        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current.strip())
            current = paragraph

    if current:
        chunks.append(current.strip())

    return [chunk for chunk in chunks if chunk]


def _build_index():
    global _kb_cache_signature, _kb_chunks_cache, _kb_embeddings_cache

    files = _list_knowledge_files()
    signature = _build_signature(files) if files else ""

    if signature == _kb_cache_signature and _kb_embeddings_cache is not None:
        return _kb_embeddings_cache, _kb_chunks_cache

    chunks = []
    for path in files:
        try:
            text = _read_file_text(path)
        except Exception:
            text = ""
        if not text:
            continue

        source_name = os.path.splitext(os.path.basename(path))[0]
        for chunk_text in _split_into_chunks(text):
            chunks.append({
                "source": source_name,
                "path": path,
                "content": chunk_text,
            })

    if not chunks:
        _kb_cache_signature = signature
        _kb_chunks_cache = []
        _kb_embeddings_cache = None
        return None, []

    embeddings = model.encode([chunk["content"] for chunk in chunks], convert_to_numpy=True)
    _kb_cache_signature = signature
    _kb_chunks_cache = chunks
    _kb_embeddings_cache = embeddings
    return embeddings, chunks


def get_document_text_by_source(source_name):
    """Return the raw text for a document source name (without extension)."""
    if not source_name:
        return ""

    target = str(source_name).strip().lower()
    for path in _list_knowledge_files():
        current_source = os.path.splitext(os.path.basename(path))[0].strip().lower()
        if current_source == target:
            try:
                return _read_file_text(path)
            except Exception:
                return ""
    return ""


def _parse_section_lines(text):
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def build_case_studies_reply(max_projects=3):
    """Build a structured reply from case study documents."""
    text = get_document_text_by_source("case_studies")
    lines = _parse_section_lines(text)
    if not lines:
        return ""

    projects = []
    current = None

    for line in lines:
        lower = line.lower()
        if lower.startswith("project "):
            if current:
                projects.append(current)
            current = {"title": line, "budget": "", "scope": "", "highlights": []}
            continue

        if current is None:
            continue

        if lower.startswith("budget:"):
            current["budget"] = line.split(":", 1)[1].strip()
        elif lower.startswith("scope:"):
            current["scope"] = line.split(":", 1)[1].strip()
        elif lower.startswith("highlights:"):
            highlight = line.split(":", 1)[1].strip()
            if highlight:
                current["highlights"].append(highlight)
        elif line.startswith("-") or line.startswith("•"):
            current["highlights"].append(line.lstrip("-• ").strip())

    if current:
        projects.append(current)

    if not projects:
        return ""

    selected = projects[:max_projects]
    parts = ["Here are a few past projects we can share:"]

    for project in selected:
        parts.append(f"- {project['title']}")
        if project.get("budget"):
            parts.append(f"  Budget: {project['budget']}")
        if project.get("scope"):
            parts.append(f"  Scope: {project['scope']}")
        if project.get("highlights"):
            highlight_text = "; ".join(project["highlights"][:3])
            parts.append(f"  Highlights: {highlight_text}")

    parts.append(
        "If you want, I can also narrow this down by 1BHK, 2BHK, 3BHK, or office style."
    )
    return "\n".join(parts)


def build_materials_quality_breakdown():
    """Build breakdown of materials by quality level (budget/premium/luxury)."""
    text = get_document_text_by_source("materials")
    lines = _parse_section_lines(text)
    if not lines:
        return None

    quality_items = []
    in_quality_section = False
    for line in lines:
        normalized = line.strip()
        lower = normalized.lower()
        if lower == "quality levels:":
            in_quality_section = True
            continue

        if in_quality_section and normalized.endswith(":") and lower != "quality levels:":
            break

        if in_quality_section and normalized and not lower.startswith("spacestalk"):
            item = normalized.lstrip("-•* ").strip()
            if any(k in item.lower() for k in ["budget", "premium", "luxury"]):
                quality_items.append(item)

    if quality_items:
        parts = ["Material breakdown by quality level:", ""]
        for item in quality_items:
            parts.append(f"- {item}")
        return "\n".join(parts)

    return None


def build_materials_reply():
    """Build a structured reply from materials document."""
    text = get_document_text_by_source("materials")
    lines = _parse_section_lines(text)
    if not lines:
        return ""

    sections = {
        "Core Materials Used:": [],
        "Modular Components:": [],
        "Quality Levels:": [],
        "Focus Areas:": [],
    }

    current_section = None
    for line in lines:
        if line in sections:
            current_section = line
            continue
        if current_section and not line.lower().startswith("spacestalk"):
            if line.startswith("-") or line.startswith("•"):
                sections[current_section].append(line.lstrip("-• ").strip())
            elif ":" not in line:
                sections[current_section].append(line)

    parts = ["Typical materials and finishes used in our projects:"]
    if sections["Core Materials Used:"]:
        parts.append("Core materials:")
        for item in sections["Core Materials Used:"][:8]:
            parts.append(f"- {item}")

    if sections["Modular Components:"]:
        parts.append("Modular components:")
        for item in sections["Modular Components:"][:6]:
            parts.append(f"- {item}")

    if sections["Quality Levels:"]:
        parts.append("Quality levels:")
        for item in sections["Quality Levels:"][:6]:
            parts.append(f"- {item}")

    if sections["Focus Areas:"]:
        parts.append("What we optimize for:")
        for item in sections["Focus Areas:"][:5]:
            parts.append(f"- {item}")

    parts.append(
        "If you want, I can also break this down for budget, premium, or luxury interiors."
    )
    return "\n".join(parts)


def search_knowledge_base(query, threshold=0.35):
    """
    Search local documents semantically.
    Returns (answer, source, score) or (None, None, 0).
    """
    if not query or len(query.strip()) < 2:
        return None, None, 0

    embeddings, chunks = _build_index()
    if embeddings is None or not chunks:
        return None, None, 0

    query_embedding = model.encode(query, convert_to_numpy=True)
    scores = np.dot(embeddings, query_embedding) / (
        np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_embedding)
    )

    best_idx = int(np.argmax(scores))
    best_score = float(scores[best_idx])

    if best_score >= threshold:
        chunk = chunks[best_idx]
        return chunk["content"], chunk["source"], best_score

    return None, None, best_score


def get_knowledge_base_context(query=None, top_k=3, min_score=0.25):
    """
    Return relevant document snippets for Gemini context.
    """
    embeddings, chunks = _build_index()
    if embeddings is None or not chunks:
        return ""

    if query:
        query_embedding = model.encode(query, convert_to_numpy=True)
        scores = np.dot(embeddings, query_embedding) / (
            np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_embedding)
        )
        ranked = sorted(
            [(float(score), idx) for idx, score in enumerate(scores)],
            reverse=True,
        )
        selected = [chunks[idx] for score, idx in ranked[:top_k] if score >= min_score]
    else:
        selected = chunks[:top_k]

    if not selected:
        return ""

    parts = ["=== KNOWLEDGE BASE DOCS ==="]
    for chunk in selected:
        parts.append(f"Source: {chunk['source']}\n{chunk['content'][:700]}")
    return "\n\n".join(parts)
