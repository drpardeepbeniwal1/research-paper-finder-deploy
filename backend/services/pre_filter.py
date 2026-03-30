"""
Fast pre-filter — eliminates obviously irrelevant papers BEFORE LLM scoring.
Uses zero LLM calls. Saves 30-50% of LLM RPM budget.

Logic: A paper passes if it contains at least one core concept from the query
AND does not contain any hard-exclude terms in its title.
"""
import re

def _tokenize(text: str) -> set[str]:
    """Extract meaningful words (>3 chars) from text."""
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    return set(words)

def _build_core_tokens(terms: list[str]) -> set[str]:
    """Build a set of meaningful tokens from query terms."""
    tokens: set[str] = set()
    for term in terms[:6]:  # Only use first 6 terms
        tokens.update(_tokenize(term))
    # Remove overly common academic words that appear in everything
    noise = {"study", "research", "paper", "analysis", "review", "novel",
             "using", "based", "approach", "method", "results", "data",
             "proposed", "model", "system", "learning", "deep", "neural"}
    return tokens - noise

def pre_filter(
    paper: dict,
    query_terms: list[str],
    exclude_terms: list[str],
) -> tuple[bool, str]:
    """
    Returns (should_score_with_llm: bool, reason: str).
    False means: skip LLM, assign score 5 (auto-rejected).
    """
    title = (paper.get("title") or "").strip()
    abstract = (paper.get("abstract") or "").strip()

    # Skip papers with no title at all
    if not title:
        return False, "no title"

    title_lower = title.lower()
    text_lower = (title + " " + abstract).lower()

    # Hard exclude: if any exclude term appears in the TITLE, skip
    for exc in exclude_terms:
        exc_lower = exc.lower().strip()
        if exc_lower and exc_lower in title_lower:
            return False, f"excluded term in title: {exc}"

    # Build core concept tokens from query terms
    core_tokens = _build_core_tokens(query_terms)

    # If we can't build any meaningful tokens, let LLM decide
    if not core_tokens:
        return True, "no filter tokens"

    # Paper text tokens
    text_tokens = _tokenize(text_lower)

    # Must match at least 1 core token in title, OR at least 2 in full text
    title_tokens = _tokenize(title_lower)
    title_matches = len(core_tokens & title_tokens)
    text_matches = len(core_tokens & text_tokens)

    # Generous threshold — we only reject the obvious noise
    if title_matches >= 1 or text_matches >= 2:
        return True, "passed"

    # No title match and very few text matches → likely noise
    return False, "no concept overlap"

def apply_pre_filter(
    papers: list[dict],
    query_terms: list[str],
    exclude_terms: list[str],
) -> tuple[list[dict], list[dict]]:
    """
    Split papers into (to_score, pre_rejected).
    pre_rejected gets score=5 automatically (goes to rejected PDF).
    """
    to_score: list[dict] = []
    pre_rejected: list[dict] = []

    for paper in papers:
        passes, reason = pre_filter(paper, query_terms, exclude_terms)
        if passes:
            to_score.append(paper)
        else:
            paper["relevance_score"] = 5.0
            paper["relevance_reasoning"] = f"Pre-filtered: {reason}"
            pre_rejected.append(paper)

    return to_score, pre_rejected
