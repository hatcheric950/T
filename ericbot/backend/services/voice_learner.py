import re
from collections import Counter
from typing import List, Dict


VALID_CATEGORIES = {"email", "phone", "text", "social", "sales"}


def extract_patterns(samples: List[str]) -> Dict:
    """Pull stylistic signals out of raw text samples."""
    all_text = " ".join(samples)
    words = re.findall(r"\b\w+\b", all_text.lower())

    greetings = []
    closings = []
    for s in samples:
        lines = s.strip().splitlines()
        if lines:
            greetings.append(lines[0].strip())
        if len(lines) > 1:
            closings.append(lines[-1].strip())

    # Count filler/signature words
    word_freq = Counter(words)
    top_words = [w for w, _ in word_freq.most_common(30) if len(w) > 3]

    avg_sentence_len = _avg_sentence_length(all_text)
    uses_contractions = _contraction_ratio(all_text)
    formality = _formality_score(all_text)

    return {
        "common_greetings": greetings[:5],
        "common_closings": closings[:5],
        "signature_words": top_words[:15],
        "avg_sentence_length": round(avg_sentence_len, 1),
        "uses_contractions": uses_contractions,
        "formality_score": round(formality, 2),
    }


def _avg_sentence_length(text: str) -> float:
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return 0.0
    lengths = [len(s.split()) for s in sentences]
    return sum(lengths) / len(lengths)


def _contraction_ratio(text: str) -> bool:
    contractions = len(re.findall(r"\b\w+'\w+\b", text))
    words = len(re.findall(r"\b\w+\b", text))
    return (contractions / max(words, 1)) > 0.03


def _formality_score(text: str) -> float:
    informal_markers = ["hey", "gonna", "wanna", "tbh", "lol", "haha", "man", "dude", "bro", "yeah"]
    formal_markers = ["sincerely", "regards", "dear", "pursuant", "herewith", "accordingly"]
    lower = text.lower()
    informal = sum(lower.count(m) for m in informal_markers)
    formal = sum(lower.count(m) for m in formal_markers)
    total = informal + formal
    if total == 0:
        return 0.5
    return formal / total


def build_style_context(patterns_by_category: Dict) -> str:
    """Produce a plain-English style guide from extracted patterns."""
    if not patterns_by_category:
        return "No voice samples loaded yet. Respond naturally but professionally."

    lines = ["Eric's Communication Style Guide:", ""]
    for cat, p in patterns_by_category.items():
        lines.append(f"[{cat.upper()}]")
        if p.get("common_greetings"):
            lines.append(f"  Greetings: {', '.join(p['common_greetings'][:3])}")
        if p.get("common_closings"):
            lines.append(f"  Sign-offs: {', '.join(p['common_closings'][:3])}")
        if p.get("signature_words"):
            lines.append(f"  Signature vocab: {', '.join(p['signature_words'][:8])}")
        lines.append(f"  Avg sentence length: {p.get('avg_sentence_length', 'N/A')} words")
        lines.append(f"  Contractions: {'yes' if p.get('uses_contractions') else 'no'}")
        lines.append(f"  Formality (0=casual, 1=formal): {p.get('formality_score', 0.5)}")
        lines.append("")

    return "\n".join(lines)


def confidence_score(sample_count: int) -> float:
    """0.0–1.0 based on how many samples exist."""
    thresholds = [1, 5, 10, 20, 50]
    for i, t in enumerate(thresholds):
        if sample_count < t:
            return i * 0.2
    return 1.0
