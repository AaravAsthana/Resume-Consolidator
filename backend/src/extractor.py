import os
import re
import json
from typing import List, Tuple, Optional, Dict

import fitz               # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image
import spacy
from dotenv import load_dotenv

# ─── Load Secrets for OCR if needed ─────────────────────────────────────────────
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# ─── Initialize spaCy model ─────────────────────────────────────────────────────
nlp = spacy.load("en_core_web_sm")

# ─── Section heading keywords ──────────────────────────────────────────────────
SECTION_KEYWORDS = {
    "profile": ["profile", "summary", "objective"],
    "experience": ["experience", "professional experience", "work experience", "employment history", "work history"],
    "education": ["education", "academic background", "qualifications"],
    "skills": ["skills", "skill set", "technical skills", "competencies"],
    "projects": ["projects", "personal projects", "portfolio"],
    "certifications": ["certifications", "licenses", "credentials"],
    "achievements": ["achievements", "awards", "honors"],
    "volunteer_experience": ["volunteer", "volunteer work", "activities", "extracurricular activities"],
    "references": ["reference", "references"]
}

# ─── Regex patterns ─────────────────────────────────────────────────────────────
EMAIL_REGEX = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
PHONE_REGEX = (
    r"(?:\+?\d{1,3}[-.\s]*)?"      # country code
    r"(?:\(?\d{2,4}\)?[-.\s]*)?"   # area code
    r"\d{3,4}[-.\s]?\d{3,4}"       # number
    r"(?:\s*(?:x|ext\.?)+\s*\d{1,5})?"  # extension
)
LINKEDIN_REGEX = r"(?:https?://)?(?:www\.)?linkedin\.com/[^\s/]+(?:/[^\s/]+)?"
GITHUB_REGEX   = r"^(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_-]+/?$"

# ─── Text & Link Extraction ────────────────────────────────────────────────────
def extract_text_and_links(path: str) -> Tuple[str, List[str]]:
    text, links = "", set()
    doc = fitz.open(path)
    for page in doc:
        text += page.get_text()
        for link in page.get_links():
            uri = link.get("uri")
            if uri:
                links.add(uri.rstrip("/"))
    if len(text) < 50:
        with pdfplumber.open(path) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    if len(text) < 50:
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text += "\n" + pytesseract.image_to_string(img)
    return text, list(links)


def extract_image(path: str) -> Optional[bytes]:
    doc = fitz.open(path)
    for page in doc:
        for img_ref in page.get_images(full=True):
            xref = img_ref[0]
            img_dict = doc.extract_image(xref)
            if img_dict and img_dict.get("image"):
                return img_dict["image"]
    return None

# ─── Sectioning Utilities ────────────────────────────────────────────────────
def split_lines(text: str) -> List[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def debug_headings(lines: List[str]) -> List[Tuple[int, str, str]]:
    """
    Identify ALL headings in the resume.
    Returns (line_index, heading_text, key) where key is either a known section key,
    or a sanitized version of the heading text (lowercase, underscores).
    """
    hs = []
    for i, ln in enumerate(lines):
        low = ln.lower().strip()
        matched = False
        # check known sections first
        for sec, kws in SECTION_KEYWORDS.items():
            if any(low.startswith(k) for k in kws):
                hs.append((i, ln.strip(), sec))
                matched = True
                break
        if matched:
            continue
        # detect any line ending in ':' or in all caps as heading
        if ln.endswith(':') or (ln.isupper() and len(ln.split()) < 6):
            key = ln.rstrip(':').lower().replace(' ', '_')
            hs.append((i, ln.strip(), key))
    return hs


def find_section_bounds(
    heads: List[Tuple[int, str, str]], target: str
) -> Tuple[Optional[int], Optional[int]]:
    for idx, (ln, _, sec) in enumerate(heads):
        if sec == target:
            start = ln + 1
            end = heads[idx + 1][0] if idx + 1 < len(heads) else None
            return start, end
    return None, None


def extract_section(
    lines: List[str], start: Optional[int], end: Optional[int]
) -> Optional[str]:
    if start is None or start >= len(lines):
        return None
    return "\n".join(lines[start:(end or len(lines))]).strip()

# ─── Field Extractors ────────────────────────────────────────────────────────
def extract_name(lines: List[str]) -> Optional[str]:
    pat = r"^[A-Z][a-zA-Z’'-]+(?:\s+[A-Z][a-zA-Z’'-]+){0,3}$"
    for ln in lines[:10]:
        if re.match(pat, ln):
            return ln
    doc = nlp(" ".join(lines[:50]))
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text
    return None


def extract_email(text: str) -> Optional[str]:
    m = re.search(EMAIL_REGEX, text)
    return m.group() if m else None


def extract_phone(text: str) -> Optional[str]:
    m = re.search(PHONE_REGEX, text)
    if not m:
        return None
    raw = m.group()
    digits = re.sub(r"\D", "", raw)
    return raw.strip() if len(digits) >= 10 else None


def extract_linkedin(text: str, links: List[str]) -> Optional[str]:
    for uri in links:
        if re.match(LINKEDIN_REGEX, uri):
            return uri
    m = re.search(LINKEDIN_REGEX, text)
    return m.group().rstrip("/") if m else None


def extract_github(text: str, links: List[str]) -> Optional[str]:
    for uri in links:
        if re.match(GITHUB_REGEX, uri):
            return uri
    m = re.search(GITHUB_REGEX, text, flags=re.IGNORECASE)
    return m.group().rstrip("/") if m else None


def extract_skills(section: Optional[str]) -> List[str]:
    if not section:
        return []
    tokens = []
    for part in re.split(r"[,\n]", section):
        part = part.strip()
        if not part:
            continue
        for token in re.split(r"[;/]", part):
            tok = token.strip()
            if len(tok) >= 2 and tok.lower() not in [t.lower() for t in tokens]:
                tokens.append(tok)
    return tokens
