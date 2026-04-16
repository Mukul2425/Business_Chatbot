"""
Semantic search service using embeddings for FAQ and knowledge base retrieval.
Provides semantic similarity scoring and confidence-based answers.
"""
from sentence_transformers import SentenceTransformer
import numpy as np
from app.services.sheets_service import get_faq, get_pricing


# Initialize embedding model (lightweight, no API needed)
# Using a smaller model that's faster and good enough for FAQ retrieval
model = SentenceTransformer("all-MiniLM-L6-v2")

# Cache for embeddings
_faq_embeddings_cache = None
_pricing_embeddings_cache = None
_faq_data_cache = None
_pricing_data_cache = None


def _build_faq_embeddings():
    """Build embeddings for all FAQ entries"""
    global _faq_embeddings_cache, _faq_data_cache
    
    faq_df = get_faq()
    if faq_df is None or len(faq_df) == 0:
        return None, []
    
    # Combine question and keywords for better search
    faq_texts = []
    faq_records = []
    
    for _, row in faq_df.iterrows():
        question = str(row.get("Question", "")).strip()
        keywords = str(row.get("Keywords", "")).strip()
        answer = str(row.get("Answer", "")).strip()
        
        if question or keywords:
            combined_text = f"{question} {keywords}".strip()
            faq_texts.append(combined_text)
            faq_records.append({
                "question": question,
                "answer": answer,
                "keywords": keywords,
            })
    
    if not faq_texts:
        return None, []
    
    embeddings = model.encode(faq_texts, convert_to_numpy=True)
    _faq_embeddings_cache = embeddings
    _faq_data_cache = faq_records
    return embeddings, faq_records


def _build_pricing_embeddings():
    """Build embeddings for pricing categories and descriptions"""
    global _pricing_embeddings_cache, _pricing_data_cache
    
    pricing_df = get_pricing()
    if pricing_df is None or len(pricing_df) == 0:
        return None, []
    
    pricing_texts = []
    pricing_records = []
    
    for _, row in pricing_df.iterrows():
        category = str(row.get("Category", "")).strip()
        min_price = str(row.get("Min Price", "")).strip()
        max_price = str(row.get("Max Price", "")).strip()
        notes = str(row.get("Notes", "")).strip()
        
        if category:
            combined_text = f"{category} {notes}".strip()
            pricing_texts.append(combined_text)
            pricing_records.append({
                "category": category,
                "min": min_price,
                "max": max_price,
                "notes": notes,
            })
    
    if not pricing_texts:
        return None, []
    
    embeddings = model.encode(pricing_texts, convert_to_numpy=True)
    _pricing_embeddings_cache = embeddings
    _pricing_data_cache = pricing_records
    return embeddings, pricing_records


def search_semantic(query, threshold=0.35):
    """
    Semantic search across FAQ.
    Returns (answer, question, score) or (None, None, 0) if no good match.
    
    threshold: minimum cosine similarity (0-1). Higher = stricter matching.
    """
    if not query or len(query.strip()) < 2:
        return None, None, 0
    
    embeddings, records = _build_faq_embeddings()
    if embeddings is None or len(records) == 0:
        return None, None, 0
    
    query_embedding = model.encode(query, convert_to_numpy=True)
    
    # Cosine similarity
    scores = np.dot(embeddings, query_embedding) / (
        np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_embedding)
    )
    
    best_idx = np.argmax(scores)
    best_score = float(scores[best_idx])
    
    if best_score >= threshold:
        record = records[best_idx]
        return record["answer"], record["question"], best_score
    
    return None, None, best_score


def search_pricing_semantic(query, threshold=0.30):
    """
    Semantic search for pricing/product categories.
    Returns (category_info, score) or (None, 0).
    """
    if not query or len(query.strip()) < 2:
        return None, 0
    
    embeddings, records = _build_pricing_embeddings()
    if embeddings is None or len(records) == 0:
        return None, 0
    
    query_embedding = model.encode(query, convert_to_numpy=True)
    
    scores = np.dot(embeddings, query_embedding) / (
        np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_embedding)
    )
    
    best_idx = np.argmax(scores)
    best_score = float(scores[best_idx])
    
    if best_score >= threshold:
        return records[best_idx], best_score
    
    return None, best_score


def generate_clarifying_question(query, missed_intents=None):
    """
    Generate a clarifying question when confidence is medium.
    Returns a user-friendly question to disambiguate.
    """
    text = (query or "").lower()
    
    clarifying_templates = {
        "budget": "Are you asking about budget for materials, labor, or total project cost?",
        "timeline": "Do you mean design timeline or actual execution timeline?",
        "customization": "Are you looking for cosmetic upgrades or structural/layout changes?",
        "process": "Do you want to know about our design approval process or execution steps?",
        "service": "Are you interested in a full home makeover or specific room design?",
    }
    
    if "budget" in text and "timeline" in text:
        return clarifying_templates["budget"]
    elif "timeline" in text:
        return clarifying_templates["timeline"]
    elif "custom" in text:
        return clarifying_templates["customization"]
    elif "process" in text:
        return clarifying_templates["process"]
    elif any(k in text for k in ["bhk", "office", "design", "interior"]):
        return clarifying_templates["service"]
    
    return "Could you clarify a bit more about your question?"


def confidence_level(score):
    """Classify confidence into high/medium/low based on score"""
    if score >= 0.65:
        return "high"
    elif score >= 0.40:
        return "medium"
    else:
        return "low"
