import streamlit as st
from docx import Document
import re
from datetime import datetime

# -------------------------
# Load family.docx directly from repo
# -------------------------
@st.cache_data
def load_family_doc(path="Family.docx"):
    doc = Document(path)
    text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    return text

# -------------------------
# Parse profiles
# -------------------------
def parse_profiles(text):
    profiles = []
    raw_profiles = text.split("\n\n")
    for raw in raw_profiles:
        if not raw.strip():
            continue
        profile = {"full_text": raw}
        # Extract fields
        name_match = re.search(r"Name:\s*(.*)", raw, re.IGNORECASE)
        alias_match = re.search(r"Alias:\s*(.*)", raw, re.IGNORECASE)
        birth_match = re.search(r"Birth Year:\s*(\d{4})", raw, re.IGNORECASE)

        if name_match:
            profile["name"] = name_match.group(1).strip()
        if alias_match:
            profile["alias"] = alias_match.group(1).strip()
        if birth_match:
            profile["birth_year"] = int(birth_match.group(1))

        profiles.append(profile)
    return profiles

# -------------------------
# Profession detection
# -------------------------
profession_keywords = {
    "doctor": ["doctor", "dr", "medicine", "surgeon"],
    "engineer": ["engineer", "engineering", "software", "mechanical"],
    "teacher": ["teacher", "professor", "lecturer"],
}

def detect_profession(text, target):
    for kw in profession_keywords.get(target, []):
        if kw.lower() in text.lower():
            return True
    return False

# -------------------------
# Handle analytical queries
# -------------------------
def handle_analytical_question(prompt, profiles):
    prompt_lower = prompt.lower()
    target_group_keyword = None

    for group in profession_keywords.keys():
        if group in prompt_lower:
            target_group_keyword = group
            break

    if target_group_keyword:  # Profession query
        group_members = [
            p for p in profiles if detect_profession(p['full_text'], target_group_keyword)
        ]
        if not group_members:
            return f"⚠️ No family members identified as **{target_group_keyword}**."
        result = [f"- **{p.get('alias','')}** ({p.get('name','')})" for p in group_members]
        return f"Here are the family members identified as **{target_group_keyword.title()}s**:\n" + "\n".join(result)

    if any(k in prompt_lower for k in ["oldest", "youngest", "rank", "list", "how many"]):
        group_members = [p for p in profiles if p.get("birth_year")]
        if not group_members:
            return "⚠️ No valid birth years found."

        if "how many" in prompt_lower:
            return f"There are **{len(group_members)}** members with known birth years."

        sorted_members = sorted(group_members, key=lambda x: x["birth_year"])
        lines = [
            f"{i+1}. {p.get('alias','')} ({p.get('name','')}), born {p['birth_year']}"
            for i, p in enumerate(sorted_members)
        ]
        return "\n".join(lines)

    return None

# -------------------------
# Streamlit UI
# -------------------------
st.title("👨‍👩‍👧‍👦 Family Chatbot")

# Load once
family_text = load_family_doc("Family.docx")
profiles = parse_profiles(family_text)

query = st.text_input("Ask about your family:")

if query:
    answer = handle_analytical_question(query, profiles)
    if not answer:  # fallback simple
        answer = "🤔 I don’t have a structured answer. Try rephrasing!"
    st.markdown(answer)
