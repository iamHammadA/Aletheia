import json
import logging
import re
from download import fetch_arxiv_as_json_with_fulltext

# Suppress pdfminer font warnings
logging.getLogger("pdfminer").setLevel(logging.ERROR)

try:
    import wordninja
    _HAS_WORDNINJA = True
except ImportError:
    _HAS_WORDNINJA = False

def mean_calculator(paragraphs):
    if not paragraphs:
        return 0
    return sum(len(p) for p in paragraphs) / len(paragraphs)

def raw_text_collector(new_text, i_clean):
    new_text.append(i_clean)


def fix_spacing(text):
    spaced = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', text)
    spaced = re.sub(r'(?<=[A-Z])(?=[A-Z][a-z])', ' ', spaced)

    tokens = spaced.split(" ")
    fixed_tokens = []
    for tok in tokens:
        if _HAS_WORDNINJA and tok.isalpha() and tok[1:].islower() and len(tok) > 10:
            lead_upper = tok[0].isupper()
            segmented = wordninja.split(tok.lower())
            if segmented and len(segmented) > 1:
                if lead_upper:
                    segmented[0] = segmented[0].capitalize()
                fixed_tokens.append(" ".join(segmented))
            else:
                fixed_tokens.append(tok)
        else:
            fixed_tokens.append(tok)
    return " ".join(fixed_tokens)


def _extract_paragraphs(raw_text):
    """Normalize full_text (str or list of blocks) into a list of clean lines."""
    if isinstance(raw_text, str):
        paragraphs = [line.strip() for line in raw_text.split("\n") if line.strip()]
    elif isinstance(raw_text, list):
        full_str = "\n".join([p if isinstance(p, str) else p.get("text", "") for p in raw_text])
        paragraphs = [line.strip() for line in full_str.split("\n") if line.strip()]
    else:
        paragraphs = []
    return paragraphs

def _extract_headings_from_paragraphs(paragraphs):
    global post_content
    """Core heading-detection heuristic, applied to a single paper's paragraphs."""
    content = {}
    ttl_score = []
    cleared_text = []
    new_text = []

    # --- UNIVERSAL REGEX PATTERNS ---
    BODY_VERBS_REGEX = r'\b(is|are|was|were|has|have|been|shows|proposes|introduces|generates|demonstrates|suggests)\b'
    DANGLING_ENDINGS = r'\b(in|of|and|or|that|for|with|to|by|at|on|the|a|an)$'

    # Universal section prefix stripper (Strips "1", "1.", "1. ", "IV.", "A.", etc.)
    HEADING_PREFIX_PATTERN = r'^([0-9]+|[IVXLCDMivxlcdm]+|[A-Z])[\.\s]*'

    # Matches sub-section numbering formats (e.g. "1.1", "2.3.1", "A.1")
    SUBHEADING_NUMBER_PATTERN = r'^(\d+\.\d+|\d+\.\d+\.\d+|[A-Z]\.\d+)\b'

    REF_MARKERS = ['[online]', 'available at:', '[accessed', 'doi:', 'http://', 'https://']

    # Common drop-cap extraction artifacts (big first letter of a heading gets
    # pulled out as its own text block by the PDF parser, leaving the remainder)
    DROP_CAP_FRAGMENTS = {
        "bstract", "ntroduction", "onclusion", "eferences", "ethodology",
        "esults", "iscussion", "ackground", "elated works", "elatedworks",
        "cknowledgements", "ppendix", "valuation", "odels", "ethod",
    }

    EMOJI_PATTERN = re.compile(
        "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]"
    )

    mean_len = mean_calculator(paragraphs)

    for idx, raw_line in enumerate(paragraphs):
        i_clean = raw_line.strip()
        if not i_clean:
            continue
        print(i_clean)
        raw_text_collector(new_text, i_clean)
        # Bullet / list-item lines (e.g. "• SomeRepo/Some-Dataset") are not headings
        if re.match(r'^[•\-\*\u2022]\s*', i_clean):
            continue

        # Lines that are mostly digits/whitespace/punctuation (chart axis labels, etc.)
        digit_ratio = sum(c.isdigit() for c in i_clean) / max(len(i_clean.replace(" ", "")), 1)
        if digit_ratio > 0.5:
            continue

        # Lines containing a path/URL-like slash (repo names, dataset links)
        if "/" in i_clean:
            continue

        # Emoji or curly/smart quotes indicate dialogue/example text, not headings
        if EMOJI_PATTERN.search(i_clean) or re.search(r'[“”‘’"]', i_clean):
            continue

        # 1. Skip Sub-headings (e.g., "1.1 Related Work", "3.2.1 Setup")
        if re.match(SUBHEADING_NUMBER_PATTERN, i_clean):
            continue

        # 2. Skip explicit sub-section prefixes
        if re.match(r'^(sub-?section|part\s+[a-z0-9]|appendix\s+[a-z0-9])', i_clean, re.IGNORECASE):
            continue

        cleaned_text = re.sub(HEADING_PREFIX_PATTERN, "", i_clean).strip()
        if not cleaned_text:
            continue

        # Restore spacing lost during PDF extraction (e.g. "RelatedWorks" ->
        # "Related Works") before word-count/scoring checks run
        cleaned_text = fix_spacing(cleaned_text)
        words = cleaned_text.split()

        # --- UNIVERSAL HEURISTIC FILTERS ---

        # Max length rule: Headings are almost never longer than 8 words
        if len(words) > 8:
            continue

        # Top-of-page Title/Author guardrail: Skip long titles at the top
        if idx < 10 and len(words) > 4 and cleaned_text.isupper():
            continue

        # Sentence / Punctuation guardrail: Headings don't end in full stops, question marks, or colons
        if cleaned_text.endswith((".", "?", ":")):
            continue

        # Lowercase start guardrail: Real headings start with uppercase or numbers
        if cleaned_text[0].islower() and not re.match(r"^\d", cleaned_text):
            continue

        # Dangling preposition guardrail (line-wrap artifacts ending in "in", "of", "and")
        if re.search(DANGLING_ENDINGS, cleaned_text, re.IGNORECASE):
            continue

        # Mathematical expressions / LaTeX / Special characters / footnote markers
        if re.search(r'[=≈×+−^|\$\\\{\}ℛℝαβγδεζηθικλμνξοπρστυφχψω∆f\(x\)∗†‡§¶]', cleaned_text):
            continue

        # Drop-cap extraction artifacts (e.g. "BSTRACT" from "ABSTRACT" missing its
        # oversized first letter, "ODELS" from "MODELS")
        if cleaned_text.lower().strip() in DROP_CAP_FRAGMENTS:
            continue

        # Figures, Tables, Page metadata
        if re.match(r'^(figure|fig\.|table|page|word count)\s*\d*', cleaned_text, re.IGNORECASE):
            continue

        # Verb / Action sentence guardrail
        if re.search(BODY_VERBS_REGEX, cleaned_text, re.IGNORECASE) and not cleaned_text.endswith('?'):
            continue

        # Contextual reference check (Skip bibliography lines)
        context = " ".join(paragraphs[max(0, idx - 1):min(len(paragraphs), idx + 2)]).lower()
        if any(marker in context for marker in REF_MARKERS):
            continue

        # --- UNIVERSAL SCORING SYSTEM ---
        score = 0
        if len(cleaned_text) < mean_len:
            score += 3
        if cleaned_text[0].isupper():
            score += 1
        if cleaned_text.isupper():  # ALL-CAPS headers get a boost
            score += 1
        if "." in cleaned_text:
            score -= 5
        if cleaned_text.count(",") >= 2:
            score -= 2

        ttl_score.append(score)
        cleared_text.append(cleaned_text)

    # Filter candidates by positive structural score
    for text, score in zip(cleared_text, ttl_score):
        if score >= 3:
            content[text] = ""

    return content


def is_heading(json_output):
    """
    Generalized version: works across ANY number of papers returned in json_output,
    not just the first one.

    Returns:
        {
            "<paper title or id>": {heading: "" , ...},
            ...
        }
    """
    papers = json.loads(json_output)

    if isinstance(papers, dict):
        # In case a single paper dict (not wrapped in a list) is passed in
        papers = [papers]

    results = {}

    for i, paper in enumerate(papers):
        raw_text = paper.get("full_text")
        paragraphs = _extract_paragraphs(raw_text)
        if not paragraphs:
            continue

        headings = _extract_headings_from_paragraphs(paragraphs)

        # Use paper title/id if available, else fall back to index
        key = paper.get("title") or paper.get("id") or f"paper_{i}"
        results[key] = headings

    return results


if __name__ == "__main__":
    search_query = "large language models"
    max_results = 1  # now actually processes all of these, not just the first
    print(f"Fetching {max_results} paper(s) for query: '{search_query}'...")

    json_output = fetch_arxiv_as_json_with_fulltext(search_query, max_results=max_results)

    # if json_output:
    #     print("\nExtracting headings from full text of each paper...")
    all_headings = is_heading(json_output)
    print(_extract_headings_from_paragraphs(json_output))

    #     for paper_key, headings_dict in all_headings.items():
    #         detected_headings = list(headings_dict.keys())
    #         print(f"\n=== {paper_key} ===")
    #         print(f"--- Detected {len(detected_headings)} Primary Headings ---")
    #         for heading in detected_headings:
    #             print(f" • {heading}")
    # else:
    #     print("Failed to fetch paper JSON from arXiv.")