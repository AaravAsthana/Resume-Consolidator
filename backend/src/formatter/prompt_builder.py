# prompt_builder.py
import json
import os

def build_prompt(raw: dict) -> str:
    schema_path = os.path.join(os.path.dirname(__file__), "schema.json")
    with open(schema_path) as f:
        schema = json.dumps(json.load(f), indent=2)

    prompt = f"""
You are an expert resume parser. Given the following raw resume sections, extract all details into a JSON that adheres strictly to the schema shown below.

SCHEMA:
{schema}

Extract and structure the data from the resume sections below:

PROFILE:
{raw.get('profile','')}

EXPERIENCE (include company, position, location, start_date, end_date, details):
{raw.get('experience','')}

EDUCATION (include degree, institution, location, start_date, end_date, details):
{raw.get('education','')}

SKILLS:
{raw.get('skills','')}

CERTIFICATIONS:
{raw.get('certifications','')}

ACHIEVEMENTS:
{raw.get('achievements','')}

VOLUNTEER EXPERIENCE:
{raw.get('volunteer_experience','')}

REFERENCES:
{raw.get('references','')}

ANY EXTRA INFO:
{raw.get('other','')}

Output ONLY valid JSON conforming exactly to the schema.
"""
    return prompt
