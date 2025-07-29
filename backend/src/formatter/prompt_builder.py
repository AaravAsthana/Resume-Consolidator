# src/formatter/prompt_builder.py
import os
import json

def build_prompt(raw: dict) -> str:
    # Locate schema.json in the same directory as this file
    schema_path = os.path.join(os.path.dirname(__file__), "schema.json")
    with open(schema_path, encoding="utf-8") as f:
        schema = json.dumps(json.load(f), indent=2)

    return f"""
You are an expert resume parser. Return ONE JSON matching this schema:
{schema}

PROFILE:
{raw.get('profile','')}

EXPERIENCE:
{raw.get('experience','')}

EDUCATION:
{raw.get('education','')}

SKILLS:
{raw.get('skills','')}

CERTIFICATIONS:
{raw.get('certifications','')}

ACHIEVEMENTS:
{raw.get('achievements','')}

VOLUNTEER_EXPERIENCE:
{raw.get('volunteer_experience','')}

PROJECTS:
{raw.get('projects','')}

REFERENCES:
{raw.get('references','')}

ANY_EXTRA:
{raw.get('other','')}

Output ONLY valid JSON. Do not include comments, trailing commas, or markdown formatting.

"""
