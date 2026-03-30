"""
Advanced deduplication — zero tolerance for duplicate papers.
Priority: DOI > arXiv ID > Title+Year fuzzy > Title-only fuzzy
"""
import re
from rapidfuzz import fuzz

def _normalize_title(title: str) -> str:
    t = title.lower().strip()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def _extract_doi(paper: dict) -> str | None:
    doi = paper.get("doi") or ""
    if not doi:
        return None
    doi = doi.lower().strip()
    doi = re.sub(r"^https?://doi\.org/", "", doi)
    doi = re.sub(r"^doi:", "", doi)
    return doi.strip() if doi else None

def _extract_arxiv_id(paper: dict) -> str | None:
    pid = paper.get("id", "")
    if pid.startswith("arxiv:"):
        return pid.split(":")[1].split("v")[0]
    url = paper.get("url") or ""
    m = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]+)", url)
    return m.group(1) if m else None

class Deduplicator:
    """
    Stateful deduplicator for a single search session.
    Call .is_unique(paper) → bool before adding.
    """
    def __init__(self):
        self._dois: set[str] = set()
        self._arxiv_ids: set[str] = set()
        self._norm_titles: list[tuple[str, int | None]] = []  # (normalized_title, year)

    def is_unique(self, paper: dict) -> bool:
        # DOI match — definitive
        doi = _extract_doi(paper)
        if doi:
            if doi in self._dois:
                return False
            self._dois.add(doi)

        # arXiv ID match — definitive
        arxiv_id = _extract_arxiv_id(paper)
        if arxiv_id:
            if arxiv_id in self._arxiv_ids:
                return False
            self._arxiv_ids.add(arxiv_id)

        # Title fuzzy match
        title = (paper.get("title") or "").strip()
        if not title:
            return True  # can't deduplicate without title, let it through

        norm = _normalize_title(title)
        year = paper.get("year")

        for seen_norm, seen_year in self._norm_titles:
            similarity = fuzz.ratio(norm, seen_norm)
            if similarity >= 92:
                # Very high similarity → duplicate regardless of year
                return False
            if similarity >= 82 and year and seen_year and abs(year - seen_year) <= 1:
                # Likely same paper, possibly arXiv vs. published version
                return False

        self._norm_titles.append((norm, year))
        return True

def deduplicate(papers: list[dict]) -> list[dict]:
    """Deduplicate a list of papers, preserving order of first occurrence."""
    dedup = Deduplicator()
    return [p for p in papers if dedup.is_unique(p)]
