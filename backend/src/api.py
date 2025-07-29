# src/api.py
import os, uuid, json, re, traceback
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from jsonschema import validate, ValidationError
import google.generativeai as genai
from dotenv import load_dotenv
import base64

from extractor import (
    extract_text_and_links, extract_image,
    split_lines, debug_headings,
    find_section_bounds, extract_section,
    extract_name, extract_email,
    extract_phone, extract_linkedin,
    extract_github, extract_skills
)
from formatter.prompt_builder import build_prompt
from formatter.pdf_renderer import render_pdf

# ─── Config ───────────────────────────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY in .env")
genai.configure(api_key=API_KEY)
MODEL = "gemini-2.5-flash"

app = Flask(__name__)
CORS(app)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "formatter", "schema.json")
with open(SCHEMA_PATH, encoding="utf-8") as f:
    SCHEMA = json.load(f)

# ─── Cleaning Utilities ───────────────────────────────────────────────────────
def clean_misc(misc):
    clean = {}
    for k, v in misc.items():
        if v is None:
            continue
        clean[k] = v
    return clean

def clean_entries(entries):
    for entry in entries:
        for key, val in entry.items():
            if val is None:
                entry[key] = ""
    return entries

# ─── Routes ────────────────────────────────────────────────────────────────────
@app.route("/api/upload", methods=["POST"])
def upload():
    try:
        files = request.files.getlist("files")
        results = []

        for f in files:
            uid = uuid.uuid4().hex
            in_path = os.path.join(UPLOAD_DIR, f"{uid}.pdf")
            f.save(in_path)

            # 1) extract raw sections
            text, links = extract_text_and_links(in_path)
            img_bytes   = extract_image(in_path) or b"  "
            lines       = split_lines(text)
            heads       = debug_headings(lines)
            raw = {}
            for _,_,key in heads:
                s,e = find_section_bounds(heads, key)
                raw[key] = extract_section(lines, s, e) or ""

            # 2) base parsed dict
            parsed = {
                "full_name": extract_name(lines),
                "contact": {
                    "email":    extract_email(text),
                    "phone":    extract_phone(text),
                    "linkedin": extract_linkedin(text, links),
                    "github":   extract_github(text, links),
                },
                "image_bytes": base64.b64encode(img_bytes).decode("ascii") if img_bytes else "",
                "sections": {
                    "about_me": raw.get("profile", ""),
                    "education": [],
                    "experience": [],
                    "skills": [],
                    "references": raw.get("references", ""),
                    "misc": {}
                }
            }
            for sec in ("certifications", "achievements", "volunteer_experience", "projects"):
                if raw.get(sec):
                    parsed["sections"]["misc"][sec] = raw[sec]

            # 3) single Gemini call
            prompt = build_prompt(raw)
            model  = genai.GenerativeModel(MODEL)
            resp   = model.generate_content(prompt)
            clean  = re.sub(r"^```json\s*|\s*```$", "", resp.text, flags=re.IGNORECASE).strip()
            try:
                llm = json.loads(clean)
            except json.JSONDecodeError as err:
                print("LLM returned invalid JSON:", err)
                print("LLM raw output:", clean[:500])  # limit log for safety
                return jsonify({
                    "error": "invalid_llm_response",
                    "details": str(err),
                    "llm_output": clean
                }), 500

            # 4) merge LLM structured
            sec = llm["sections"]
            parsed["sections"]["education"]  = sec.get("education", [])
            parsed["sections"]["experience"] = sec.get("experience", [])
            parsed["sections"]["skills"]     = sec.get("skills", {})
            parsed["sections"]["misc"].update(sec.get("misc", {}))

            # 5) clean invalid None values before validation
            parsed["image_bytes"] = parsed.get("image_bytes") or ""
            parsed["sections"]["misc"] = clean_misc(parsed["sections"].get("misc", {}))
            parsed["sections"]["education"] = clean_entries(parsed["sections"].get("education", []))
            parsed["sections"]["experience"] = clean_entries(parsed["sections"].get("experience", []))

            # 6) validate
            validate(parsed, SCHEMA)

            # 7) render PDF
            out_path = os.path.join(UPLOAD_DIR, f"{uid}-out.pdf")
            render_pdf(parsed, out_path)

            results.append({
                "id": uid,
                "file_name": f.filename,
                "pdf_url": f"/api/result/{uid}-out.pdf"
            })

        return jsonify(results)

    except ValidationError as ve:
        traceback.print_exc()
        return jsonify({"error": "validation_failed", "details": ve.message}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "internal_error", "details": str(e)}), 500

@app.route("/api/result/<path:fn>")
def result(fn):
    return send_from_directory(UPLOAD_DIR, fn, as_attachment=False)

if __name__ == "__main__":
    app.run(port=8000, debug=True)
