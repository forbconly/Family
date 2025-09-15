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
# Parse profiles
# -----------------------------
def parse_profiles_from_text(full_text):
    profiles = []
    if not full_text:
        return profiles

    if '--- PERSON START ---' in full_text:
        chunks = [c.strip() for c in full_text.split('--- PERSON START ---') if c.strip()]
    else:
        chunks = [c.strip() for c in re.split(r'\n{2,}', full_text) if c.strip()]

    for chunk in chunks:
        p = {"full_text": chunk}

        m = re.search(r"Name:\s*(.*?)\s*(?:\(alias\s*(.*?)\))?(?:\n|$)", chunk, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            p["name"] = name
            alias = m.group(2).strip() if m.group(2) else None
            if alias:
                p["alias"] = alias
            else:
                a2 = re.search(r"Alias:\s*(.*)", chunk, re.IGNORECASE)
                p["alias"] = a2.group(1).strip() if a2 else (name.split()[0] if name else None)
        else:
            header_name = re.match(r"^([A-Z][a-z]+\s+[A-Z][a-z]+)", chunk)
            if header_name:
                p["name"] = header_name.group(1)_
