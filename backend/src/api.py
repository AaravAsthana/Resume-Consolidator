import os
import uuid
import json
from typing import List
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from jsonschema import validate, ValidationError
from google import generativeai as genai

from extractor import (
    extract_text_and_links,
    extract_image,
    split_lines,
    debug_headings,
    find_section_bounds,
    extract_section,
    extract_name,
    extract_email,
    extract_phone,
    extract_linkedin,
    extract_github,
    extract_skills,
)

from formatter.prompt_builder import build_prompt
from formatter.pdf_renderer import render_pdf

# ─── Configure Generative AI ────────────────────────────────────────────────
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL_NAME = "gemini-1.5-flash"
model = genai.GenerativeModel(MODEL_NAME)

app = Flask(__name__)
CORS(app)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

SCHEMA = json.load(open(
    os.path.join(os.path.dirname(__file__), "formatter", "schema.json")
))


@app.route("/api/upload", methods=["POST"])
def upload():
    files = request.files.getlist("files")
    responses = []

    def lines_to_list(text_block: str) -> List[str]:
        """Split raw block into non-empty lines for array fields."""
        return [ln.strip() for ln in text_block.splitlines() if ln.strip()]

    for f in files:
        uid = uuid.uuid4().hex
        in_path = os.path.join(UPLOAD_DIR, f"{uid}.pdf")
        f.save(in_path)

        # 1) Extract raw data
        text, links = extract_text_and_links(in_path)
        img_bytes = extract_image(in_path)
        lines = split_lines(text)
        heads = debug_headings(lines)

        # 2) Build dynamic raw sections
        raw = {}
        for idx, heading_text, key in heads:
            start, end = find_section_bounds(heads, key)
            raw[key] = extract_section(lines, start, end) or ""

        # 3) Construct parsed dict (experience and education as arrays)
        parsed = {
            "full_name": extract_name(lines) or "",
            "current_job": None,
            "contact": {
                "email": extract_email(text) or "",
                "phone": extract_phone(text) or "",
                "linkedin": extract_linkedin(text, links) or None,
                "github": extract_github(text, links) or None,
            },
            "image_bytes": img_bytes,

            "profile": raw.get("profile", ""),
            "experience": lines_to_list(raw.get("experience", "")),
            "education": lines_to_list(raw.get("education", "")),
            "skills": extract_skills(raw.get("skills", "")),

            "references": lines_to_list(raw.get("references", "")),
            "certifications": lines_to_list(raw.get("certifications", "")),
            "achievements": lines_to_list(raw.get("achievements", "")),
            "volunteer_experience": lines_to_list(raw.get("volunteer_experience", "")),
        }

        # 4) Enrich via Gemini‑1.5‑Flash (new version usage)
        try:
            prompt = build_prompt(raw)
            response = model.generate_content(prompt)
            llm_output = response.text.strip()
            llm_json = json.loads(llm_output)

            # Merge Gemini output
            for k, v in llm_json.items():
                if not parsed.get(k):
                    parsed[k] = v
        except Exception as e:
            parsed["_llm_error"] = str(e)

        # 5) Validate against schema
        try:
            validate(instance=parsed, schema=SCHEMA)
        except ValidationError as ve:
            return jsonify({
                "error": "validation_failed",
                "details": ve.message
            }), 400

        # 6) Render to PDF
        out_pdf = os.path.join(UPLOAD_DIR, f"{uid}-out.pdf")
        render_pdf(parsed, out_pdf)

        # 7) Build response entry
        entry = {
            "id": uid,
            "file_name": f.filename,
            "pdf_url": f"/api/result/{uid}-out.pdf"
        }
        if "_llm_error" in parsed:
            entry["llm_error"] = parsed["_llm_error"]
        responses.append(entry)

    return jsonify(responses)


@app.route("/api/result/<path:filename>")
def result(filename):
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=False)


if __name__ == "__main__":
    app.run(port=8000, debug=True)
