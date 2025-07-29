import os
import re
from typing import List, Tuple, Optional, Dict

import fitz               # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image
import spacy
from dotenv import load_dotenv

# Load .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# spaCy model
nlp = spacy.load("en_core_web_sm")

# Section keywords
SECTION_KEYWORDS = {
    "profile": ["profile", "summary", "objective"],
    "experience": ["experience", "professional experience", "work experience", "employment history"],
    "education": ["education", "academic background", "qualifications"],
    "skills": ["skills", "skill set", "technical skills", "competencies"],
    "certifications": ["certifications", "licenses", "credentials"],
    "achievements": ["achievements", "awards", "honors"],
    "volunteer_experience": ["volunteer", "activities", "extracurricular"]
}

EMAIL_REGEX    = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
PHONE_REGEX    = r"(?:\+?\d{1,3}[-.\s]*)?(?:\(?\d{2,4}\)?[-.\s]*)?\d{3,4}[-.\s]?\d{3,4}"
LINKEDIN_REGEX = r"(?:https?://)?(?:www\.)?linkedin\.com/[^\s/]+"
GITHUB_REGEX   = r"^(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_-]+/?$"

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
    """Return the first embedded image (bytes) found in the PDF, or None."""
    doc = fitz.open(path)
    for page in doc:
        for img_ref in page.get_images(full=True):
            xref = img_ref[0]
            img_dict = doc.extract_image(xref)
            if img_dict and "image" in img_dict:
                return img_dict["image"]
    return None

def split_lines(text: str) -> List[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]

def debug_headings(lines: List[str]) -> List[Tuple[int, str, str]]:
    hs = []
    for i, ln in enumerate(lines):
        low = ln.lower()
        for key, kws in SECTION_KEYWORDS.items():
            if any(low.startswith(k) for k in kws):
                hs.append((i, ln, key))
                break
    return hs

def find_section_bounds(heads, target):
    for idx, (ln_idx, _, key) in enumerate(heads):
        if key == target:
            start = ln_idx + 1
            end = heads[idx + 1][0] if idx + 1 < len(heads) else None
            return start, end
    return None, None

def extract_section(lines, start, end):
    if start is None or start >= len(lines):
        return ""
    return "\n".join(lines[start:(end or len(lines))]).strip()

def extract_name(lines: List[str]) -> str:
    pat = r"^[A-Z][a-zA-Z’'-]+(?:\s+[A-Z][a-zA-Z’'-]+){0,3}$"
    for ln in lines[:10]:
        if re.match(pat, ln):
            return ln
    doc = nlp(" ".join(lines[:50]))
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text
    return ""

def extract_email(text: str) -> str:
    m = re.search(EMAIL_REGEX, text)
    return m.group() if m else ""

def extract_phone(text: str) -> str:
    m = re.search(PHONE_REGEX, text)
    return m.group().strip() if m else ""

def extract_linkedin(text: str, links: List[str]) -> str:
    for uri in links:
        if re.match(LINKEDIN_REGEX, uri):
            return uri
    m = re.search(LINKEDIN_REGEX, text)
    return m.group() if m else ""

def extract_github(text: str, links: List[str]) -> str:
    for uri in links:
        if re.match(GITHUB_REGEX, uri):
            return uri
    m = re.search(GITHUB_REGEX, text)
    return m.group() if m else ""

def extract_skills(section: str) -> List[str]:
    if not section:
        return []
    items = re.split(r"[,\n;]", section)
    seen = set()
    out = []
    for x in items:
        t = x.strip()
        if t and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out

# at the bottom of extractor.py

def parse_grouped_skills(raw: str) -> Dict[str, List[str]]:
    """
    Split the skills block into sub‑sections.
    We assume headings are lines without commas,
    followed by comma/line‑separated items.
    """
    groups = {}
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    current = None
    for ln in lines:
        # if this line has no comma and is Title‑Case, treat it as a heading
        if ',' not in ln and ln == ln.title():
            current = ln
            groups[current] = []
        else:
            # split subitems on commas
            for token in re.split(r"[,;/]\s*", ln):
                token = token.strip()
                if token:
                    groups.setdefault(current or "Skills", []).append(token)
    return groups
