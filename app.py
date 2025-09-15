import streamlit as st
import docx
from datetime import datetime
from rapidfuzz import fuzz

# -----------------------------
# Profession Keywords
# -----------------------------
profession_keywords = {
    "doctor": ["doctor", "dr.", "mbbs", "physician", "surgeon", "pediatrician", "medicine", "medical"],
    "engineer": ["engineer", "iitian", "b.tech", "m.tech", "technology", "software", "mechanical"],
    "lawyer": ["lawyer", "advocate", "legal", "llb"],
    "ca": ["chartered accountant", "ca", "accountant", "cpa"]
}

# -----------------------------
# Load and parse Family.docx
# -----------------------------
def load_family_data(docx_file):
    doc = docx.Document(docx_file)
    profiles = []
    current_profile = {}

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        if text.startswith("Name:"):
            if current_profile:
                profiles.append(current_profile)
                current_profile = {}

            current_profile["name"] = text.replace("Name:", "").strip()
            current_profile["full_text"] = text

        elif text.startswith("Alias:"):
            current_profile["alias"] = text.replace("Alias:", "").strip()
            current_profile["full_text"] += " " + text

        elif text.startswith("Birth Year:"):
            try:
                current_profile["birth_year"] = int(text.replace("Birth Year:", "").strip())
            except:
                current_profile["birth_year"] = None
            current_profile["full_text"] += " " + text

        else:
            current_profile["full_text"] += " " + text

    if current_profile:
        profiles.append(current_profile)

    return profiles

# -----------------------------
# Profession detection
# -----------------------------
def detect_profession(profile_text, profession):
    keywords = profession_keywords.get(profession, [profession])
    return any(kw in profile_text.lower() for kw in keywords)

# -----------------------------
# Age ranking
# -----------------------------
def rank_by_age(profiles):
    available = [p for p in profiles if p.get('birth_year')]
    missing = [p for p in profiles if not p.get('birth_year')]

    sorted_members = sorted(available, key=lambda x: x['birth_year'])  # oldest first

    result = []
    for member in sorted_members:
        age = datetime.now().year - member['birth_year']
        result.append(f"- **{member['alias']}** ({member.get('name','')}) → Born {member['birth_year']}, approx. {age} years old")

    if missing:
        result.append("\n⚠️ Birth year not available for: " + ", ".join(m['alias'] for m in missing))

    return "\n".join(result)

# -----------------------------
# Fuzzy Search
# -----------------------------
def search_profiles(profiles, query, threshold=60):
    results = []
    for p in profiles:
        score = fuzz.partial_ratio(query.lower(), p['full_text'].lower())
        if score >= threshold:
            results.append((score, p))
    results.sort(reverse=True, key=lambda x: x[0])
    return [p for _, p in results]

# -----------------------------
# Analytical brain
# -----------------------------
def handle_analytical_question(prompt, profiles):
    prompt_lower = prompt.lower()
    target_group_keyword = None

    # Detect if prompt mentions a known profession
    for group in profession_keywords.keys():
        if group in prompt_lower:
            target_group_keyword = group
            break

    # Case 1: Profession query
    if target_group_keyword:
        group_members = [
            p for p in profiles
            if detect_profession(p['full_text'], target_group_keyword)
        ]

        if not group_members:
            return f"⚠️ I couldn't find anyone explicitly described as a **{target_group_keyword}** in the family."

        result = [f"- **{p['alias']}** ({p.get('name','')})" for p in group_members]
        return f"Here are the family members identified as **{target_group_keyword.title()}s**:\n" + "\n".join(result)

    # Case 2: Age-related queries
    if any(keyword in prompt_lower for keyword in ["rank", "list", "oldest", "youngest", "how many"]):
        group_members = [p for p in profiles if p.get('birth_year')]
        if not group_members:
            return "⚠️ No members have valid birth years."

        if "how many" in prompt_lower:
            return f"There are **{len(group_members)}** members with available birth year information."

        return rank_by_age(group_members)

    # Case 3: Search query
    results = search_profiles(profiles, prompt)
    if results:
        result = [f"- **{p['alias']}** ({p.get('name','')})" for p in results[:5]]
        return f"Closest matches to your query:\n" + "\n".join(result)

    # No match
    return None

# -----------------------------
# Creative brain (fallback)
# -----------------------------
def creative_response(prompt):
    return f"✨ I'm not sure from the data, but here's a fun thought about your query: *{prompt}*."

# -----------------------------
# Chatbot
# -----------------------------
def chatbot_response(prompt, profiles):
    analytical_answer = handle_analytical_question(prompt, profiles)
    if analytical_answer:
        return analytical_answer
    return creative_response(prompt)

# -----------------------------
# Streamlit UI
# -----------------------------
def main():
    st.set_page_config(page_title="Family Chatbot", page_icon="👨‍👩‍👧‍👦", layout="centered")
    st.title("👨‍👩‍👧‍👦 Family Chatbot")

    uploaded_file = st.file_uploader("Upload your Family.docx", type="docx")

    if uploaded_file:
        profiles = load_family_data(uploaded_file)
        st.success(f"Loaded {len(profiles)} family profiles!")

        user_input = st.text_input("Ask something about your family:")
        if st.button("Ask"):
            if user_input:
                response = chatbot_response(user_input, profiles)
                st.markdown(response)

if __name__ == "__main__":
    main()
