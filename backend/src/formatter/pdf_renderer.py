# src/formatter/pdf_renderer.py

import os
import io
import base64
import tempfile
import uuid
import pdfkit
from jinja2 import Environment, FileSystemLoader
from PyPDF2 import PdfReader, PdfWriter

# --- configuration for pdfkit to allow local file access ---
PDFKIT_OPTIONS = {
    'enable-local-file-access': None,
    'quiet': ''
}
WK_CONFIG = None  # if you need to point at a custom wkhtmltopdf binary

env = Environment(loader=FileSystemLoader("src/formatter/templates"))


def _render_html(template_name: str, context: dict) -> str:
    tpl = env.get_template(template_name)
    return tpl.render(**context)


def _html_to_pdf_bytes(html: str) -> bytes:
    """
    Render HTML to a temporary PDF file and return its bytes.
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        pdfkit.from_string(html, f.name, options=PDFKIT_OPTIONS, configuration=WK_CONFIG)
        f.flush()
        path = f.name
    with open(path, 'rb') as f2:
        data = f2.read()
    os.remove(path)
    return data


def render_pdf(parsed: dict, output_path: str):
    # 1) Handle embedded image if present
    image_path = None
    img_b = parsed.get("image_bytes")
    if img_b:
        try:
            tmp_img = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}.png")
            with open(tmp_img, "wb") as imgf:
                imgf.write(base64.b64decode(img_b))
            image_path = tmp_img
        except Exception:
            image_path = None

    # 2) Find how many experience entries fit on a single first page
    all_exp = parsed["sections"].get("experience", [])
    lo, hi, best = 0, len(all_exp), 0
    while lo <= hi:
        mid = (lo + hi) // 2
        ctx = {
            "full_name": parsed.get("full_name",""),
            "current_job": parsed.get("current_job",""),
            "contact": parsed.get("contact",{}),
            "about_me": parsed["sections"].get("about_me",""),
            "references": parsed["sections"].get("references","").splitlines(),
            "education": parsed["sections"].get("education",[]),
            "experience": all_exp[:mid],
            "skills": {},
            "misc": {},
            "image_path": image_path,
        }
        html1 = _render_html("resume_template_first_page.html", ctx)
        pdf_bytes = _html_to_pdf_bytes(html1)
        pages = len(PdfReader(io.BytesIO(pdf_bytes)).pages)
        if pages == 1:
            best, lo = mid, mid + 1
        else:
            hi = mid - 1

    first_exp = all_exp[:best]
    remaining_exp = all_exp[best:]

    # 3) Render and save the first‑page PDF
    ctx1 = {
        "full_name": parsed.get("full_name",""),
        "current_job": parsed.get("current_job",""),
        "contact": parsed.get("contact",{}),
        "about_me": parsed["sections"].get("about_me",""),
        "references": parsed["sections"].get("references","").splitlines(),
        "education": parsed["sections"].get("education",[]),
        "experience": first_exp,
        "skills": {},
        "misc": {},
        "image_path": image_path,
    }
    html1 = _render_html("resume_template_first_page.html", ctx1)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp1:
        pdfkit.from_string(html1, tmp1.name, options=PDFKIT_OPTIONS, configuration=WK_CONFIG)
        first_pdf = tmp1.name

    # 4) Render and save the continuation PDF
    ctx2 = {
        "education": [],
        "experience": remaining_exp,
        "skills": parsed["sections"].get("skills", {}),
        "misc": parsed["sections"].get("misc", {}),
    }
    html2 = _render_html("resume_template_continuation.html", ctx2)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp2:
        pdfkit.from_string(html2, tmp2.name, options=PDFKIT_OPTIONS, configuration=WK_CONFIG)
        cont_pdf = tmp2.name

    # 5) Merge both PDFs
    writer = PdfWriter()
    for fn in (first_pdf, cont_pdf):
        reader = PdfReader(fn)
        for p in reader.pages:
            writer.add_page(p)
    with open(output_path, "wb") as outf:
        writer.write(outf)

    # 6) Cleanup
    for fn in (first_pdf, cont_pdf, image_path):
        if fn and os.path.exists(fn):
            try: os.remove(fn)
            except: pass
