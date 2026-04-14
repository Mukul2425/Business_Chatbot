from app.services.sheets_service import get_faq


STOPWORDS = {
    "the", "and", "for", "with", "you", "your", "can", "help", "need", "want",
    "what", "when", "where", "which", "how", "are", "is", "our", "about", "please",
}


def search_faq(query, threshold=3):
    """
    Search FAQ with keyword matching.
    Returns answer if found, else None
    """
    df = get_faq()
    query_text = (query or "").strip().lower()
    query_tokens = [
        t for t in query_text.split()
        if len(t) >= 4 and t not in STOPWORDS
    ]

    best_match = None
    best_score = 0

    for _, row in df.iterrows():
        keywords = row.get("Keywords", "")
        answer = row.get("Answer", "")

        keyword_list = [k.strip().lower() for k in keywords.split(",") if k.strip()]
        score = 0
        for keyword in keyword_list:
            # Exact phrase hit in full query is strongest.
            if keyword in query_text:
                score += 3
                continue

            # Token-level exact matches only (no substring fuzziness).
            keyword_tokens = [
                t for t in keyword.split()
                if len(t) >= 4 and t not in STOPWORDS
            ]
            token_hits = sum(1 for token in keyword_tokens if token in query_tokens)
            score += token_hits * 2

        if score > best_score:
            best_score = score
            best_match = answer

    if best_score >= threshold:
        return best_match

    return None


def get_all_faq_categories():
    """Get all FAQ categories for menu"""
    df = get_faq()
    categories = df.get("Category", []).unique().tolist() if "Category" in df.columns else []
    return [cat for cat in categories if cat]


def get_faq_by_category(category):
    """Get all FAQs in a category"""
    df = get_faq()
    if "Category" not in df.columns:
        return []
    result = df[df["Category"] == category]
    return result.to_dict('records')