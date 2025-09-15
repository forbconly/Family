# app.py
import os
import re
import docx
import streamlit as st
from datetime import datetime
from rapidfuzz import fuzz
import pandas as pd

st.set_page_config(page_title="Family Chatbot (name-search + fuzzy)", page_icon="👪", layout="centered")
st.title("👨‍👩‍👧‍👦 Family Chatbot — Name & Fuzzy Search Fixes")

# -----------------------------
# Profession keywords (expandable)
# -----------------------------
profession_keywords = {
    "doctor": ["doctor", "dr.", "mbbs", "physician", "surgeon", "pediatrician", "medicine", "medical"],
    "engineer": ["engineer", "iitian", "b.tech", "m.tech", "technology", "software", "mechanical"],
    "lawyer": ["lawyer", "advocate", "legal", "llb"],
    "ca": ["chartered accountant", "ca", "accountant", "cpa"]
}

# -----------------------------
# Load docx from repo (cached)
# -----------------------------
@st.cache_data
def load_docx_text(path="Family.docx"):
    if not os.path.exists(path):
        return None
    doc = docx.Document(path)
    text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    return text

# -----------------------------
# Parse profiles (marker-style or header-style)
# -----------------------------
def parse_profiles_from_text(full_text):
    profiles = []
    if not full_text:
        return profiles

    # Marker-based split (preferred if present)
    if '--- PERSON START ---' in full_text:
        chunks = [c.strip() for c in full_text.split('--- PERSON START ---') if c.strip()]
    else:
        # Fallback: split on double newlines (blocks)
        chunks = [c.strip() for c in re.split(r'\n{2,}', full_text) if c.strip()]

    for chunk in chunks:
        p = {"full_text": chunk}
        # Try to find Name (with optional alias in parentheses)
        m = re.search(r"Name:\s*(.*?)\s*(?:\(alias\s*(.*?)\))?(?:\n|$)", chunk, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            p["name"] = name
            alias = m.group(2).strip() if m.group(2) else None
            if alias:
                p["alias"] = alias
            else:
                # try explicit Alias: line
                a2 = re.search(r"Alias:\s*(.*)", chunk, re.IGNORECASE)
                p["alias"] = a2.group(1).strip() if a2 else (name.split()[0] if name else None)
        else:
            # Try header style "Name: X" later; else try to infer first line as name
            header_name = re.match(r"^([A-Z][a-z]+\s+[A-Z][a-z]+)", chunk)
            if header_name:
                p["name"] = header_name.group(1).strip()
                p["alias"] = p["name"].split()[0]

        # Birth year detection: try explicit patterns, then any reasonable 4-digit year
        born_search = re.search(r"(?:Birth Year:|Born on|Born:|born in|was born on|born date:)\s*(?:[A-Za-z0-9,\s/-]*?)(\b(19|20)\d{2}\b)", chunk, re.IGNORECASE)
        if born_search:
            try:
                p["birth_year"] = int(born_search.group(1))
            except:
                p["birth_year"] = None
        else:
            # fallback: any 4-digit year between 1900 and current year
            any_year = re.search(r"\b(19|20)\d{2}\b", chunk)
            if any_year:
                year = int(any_year.group(0))
                if 1900 <= year <= datetime.now().year:
                    p["birth_year"] = year
                else:
                    p["birth_year"] = None
            else:
                p["birth_year"] = None

        # Profession quick extract if explicit
        prof_match = re.search(r"Profession:\s*(.*)", chunk, re.IGNORECASE)
        if prof_match:
            p["profession_line"] = prof_match.group(1).strip()
        else:
            p["profession_line"] = ""

        # Normalized lower versions for search convenience
        p["name_lower"] = p.get("name","").lower() if p.get("name") else ""
        p["alias_lower"] = p.get("alias","").lower() if p.get("alias") else ""
        p["text_lower"] = p["full_text"].lower()

        profiles.append(p)

    return profiles

# -----------------------------
# Profession detection
# -----------------------------
def detect_profession(profile, profession):
    # exact keywords in text or profession_line
    pt = profile.get("text_lower","")
    for kw in profession_keywords.get(profession, []):
        if kw in pt:
            return True
    # fuzzy fallback on profession_line and text
    for kw in profession_keywords.get(profession, []):
        if fuzz.partial_ratio(kw, profile.get("profession_line","").lower()) >= 80:
            return True
    return False

# -----------------------------
# Name & alias matching (exact then fuzzy)
# -----------------------------
def find_by_name_or_alias(profiles, name_phrase, threshold=75):
    """
    Try exact case-insensitive name/alias match first.
    If no exact match, perform fuzzy match on name+alias fields.
    Returns list of matched profiles (can be empty).
    """
    q = name_phrase.strip().lower()
    # exact match on name or alias
    exact = [p for p in profiles if p.get("name_lower")==q or p.get("alias_lower")==q]
    if exact:
        return exact

    # try partial exact (contains)
    partial = [p for p in profiles if q in p.get("name_lower","") or q in p.get("alias_lower","")]
    if partial:
        return partial

    # fuzzy on name + alias
    scored = []
    for p in profiles:
        candidates = []
        if p.get("name"):
            candidates.append(p["name"])
        if p.get("alias"):
            candidates.append(p["alias"])
        # compute best score among candidates
        best = 0
        for cand in candidates:
            s = fuzz.token_sort_ratio(q, cand.lower())
            if s > best:
                best = s
        if best >= threshold:
            scored.append((best, p))
    scored.sort(reverse=True, key=lambda x: x[0])
    return [p for _, p in scored]

# -----------------------------
# Fuzzy search across all profile text
# -----------------------------
def fuzzy_search_profiles(profiles, query, threshold=60, limit=6):
    q = query.lower()
    scored = []
    for p in profiles:
        score = fuzz.partial_ratio(q, p.get("text_lower",""))
        if score >= threshold:
            scored.append((score, p))
    scored.sort(reverse=True, key=lambda x: x[0])
    return [p for _, p in scored[:limit]]

# -----------------------------
# Age ranking
# -----------------------------
def rank_by_age(profiles):
    available = [p for p in profiles if p.get("birth_year")]
    missing = [p for p in profiles if not p.get("birth_year")]
    if not available:
        return "⚠️ No birth-year data available to rank."
    # oldest -> youngest
    available_sorted = sorted(available, key=lambda x: x["birth_year"])
    lines = []
    for p in available_sorted:
        age = datetime.now().year - p["birth_year"]
        lines.append(f"- **{p.get('alias', '(no alias)')}** ({p.get('name','')}) — Born {p['birth_year']}, ~{age} yrs")
    if missing:
        lines.append("\n⚠️ Birth year missing for: " + ", ".join(m.get("alias","(unknown)") for m in missing))
    return "\n".join(lines)

# -----------------------------
# Build readable profile text
# -----------------------------
def format_profile(p):
    lines = []
    alias = p.get("alias") or "(no alias)"
    name = p.get("name") or ""
    lines.append(f"### {alias}  {('— ' + name) if name else ''}")
    if p.get("birth_year"):
        age = datetime.now().year - p["birth_year"]
        lines.append(f"- **Born**: {p['birth_year']} (~{age} yrs)")
    if p.get("profession_line"):
        lines.append(f"- **Profession**: {p['profession_line']}")
    # show first 300 chars of full text
    snippet = p.get("full_text","").strip()
    if snippet:
        lines.append("\n" + snippet)
    return "\n".join(lines)

# -----------------------------
# Main answering logic
# -----------------------------
def answer_prompt(prompt, profiles, debug=False):
    if not profiles:
        return "No family data loaded."

    q = prompt.strip()
    q_lower = q.lower()

    # 1) Name-intent detection: "who is X", "tell me about X", "who was X"
    m = re.search(r"(?:who is|who's|who was|tell me about|about)\s+(.+)$", q_lower)
    if m:
        name_phrase = m.group(1).strip()
        # remove trailing punctuation
        name_phrase = re.sub(r"[?.!]+$", "", name_phrase).strip()
        # try direct name/alias match (use original-cased phrase too)
        matches = find_by_name_or_alias(profiles, name_phrase, threshold=70)
        if matches:
            if debug:
                dbg = [ {"alias":p.get("alias"), "name":p.get("name")} for p in matches ]
                st.write("DEBUG name-match results:", dbg)
            # return full formatted profiles
            return "\n\n".join(format_profile(p) for p in matches)

        # try fuzzy across full text
        fuzzy = fuzzy_search_profiles(profiles, name_phrase, threshold=55)
        if fuzzy:
            return "I couldn't find an exact name match. Closest matches:\n\n" + "\n\n".join(format_profile(p) for p in fuzzy)

        return f"⚠️ I couldn't find anyone matching '{name_phrase}' in the family data I parsed."

    # 2) Profession queries: e.g., "doctor in the family", "any doctors?"
    for prof in profession_keywords.keys():
        if prof in q_lower:
            matched = [p for p in profiles if detect_profession(p, prof)]
            if not matched:
                return f"⚠️ I couldn't find anyone clearly described as a **{prof}**."
            return "Here are family members identified as **" + prof.title() + "s**:\n\n" + "\n".join(f"- **{p.get('alias','') }** ({p.get('name','')})" for p in matched)

    # 3) Age/ranking/count queries
    if any(k in q_lower for k in ["rank", "list", "oldest", "youngest", "how many", "count"]):
        # if the user mentions a profession + rank, handle that too
        for prof in profession_keywords.keys():
            if prof in q_lower:
                matched = [p for p in profiles if detect_profession(p, prof) and p.get("birth_year")]
                if not matched:
                    return f"⚠️ No {prof} members with birth-year data to rank."
                return rank_by_age(matched)
        # general ranking
        return rank_by_age(profiles)

    # 4) General fuzzy search across profile text
    fuzzy = fuzzy_search_profiles(profiles, q, threshold=60)
    if fuzzy:
        return "Closest matches:\n\n" + "\n\n".join(format_profile(p) for p in fuzzy)

    return "✨ I couldn't find a structured match. Try: 'Who is <name>?', 'Doctor in the family?', 'Rank engineers by age', or enable debug to inspect parsed profiles."

# -----------------------------
# UI: load file from repo and interface
# -----------------------------
def main():
    st.markdown("This app **auto-loads `Family.docx` from the repo root**. Put your file there and redeploy / restart the app.")
    text = load_docx_text("Family.docx")
    if not text:
        st.error("No `Family.docx` found in the repo root. Please add it and refresh.")
        with st.expander("Expected formats (examples)"):
            st.markdown(
                """
**Marker style**
