import streamlit as st
from groq import Groq
import docx
import re
from datetime import datetime
from rapidfuzz import fuzz

# --- Page Configuration ---
st.set_page_config(
    page_title="The Gupta Family AI",
    page_icon="👨‍👩‍👧‍👦",
    layout="centered"
)

# --- UI Title and Description ---
st.title("👨‍👩‍👧‍👦 The Gupta Family AI Assistant")
st.markdown("""
Welcome! I'm your personal AI assistant, now with an upgraded 'Analyst' brain for factual questions!

Ask me to 'rank the engineers by age' or something fun like 'Tell me a funny story about someone'.
""")

# --- Groq API Client Initialization ---
try:
    groq_api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=groq_api_key)
except Exception:
    st.error("Groq API key not found! Please add it to your Streamlit secrets.")
    st.stop()

# --- Profession Keywords (expandable) ---
profession_keywords = {
    "doctor": ["doctor", "dr.", "mbbs", "physician", "surgeon", "pediatrician", "medicine", "medical"],
    "engineer": ["engineer", "iitian", "b.tech", "m.tech", "technology", "software", "mechanical"],
    "lawyer": ["lawyer", "advocate", "legal", "llb"],
    "ca": ["chartered accountant", "ca", "accountant", "cpa"]
}

def detect_profession(profile_text, profession):
    """Check if a profile matches a profession by fuzzy keyword search."""
    keywords = profession_keywords.get(profession, [profession])
    return any(kw in profile_text.lower() for kw in keywords)

# --- Data Parsing and Structuring ---
@st.cache_data(show_spinner="Reading and analyzing the family chronicles...")
def parse_family_document(file_path="Family.docx"):
    try:
        doc = docx.Document(file_path)
        full_text = "\n".join([para.text for para in doc.paragraphs])
        profiles_text = full_text.split("--- PERSON START ---")[1:]

        structured_profiles = []
        for profile_str in profiles_text:
            person_data = {'full_text': profile_str.strip()}

            # Extract Name and Alias
            name_match = re.search(r"Name:\s*(.*?)\s*\(alias\s*(.*?)\)", profile_str, re.IGNORECASE)
            if name_match:
                person_data['name'] = name_match.group(1).strip()
                person_data['alias'] = name_match.group(2).strip()
            else:
                name_match_simple = re.search(r"Name:\s*(.*)", profile_str, re.IGNORECASE)
                if name_match_simple:
                    person_data['name'] = name_match_simple.group(1).strip()
                    person_data['alias'] = person_data['name'].split()[0]

            # Extract Birth Year
            born_match = re.search(r"(?:born on|born in year|born in|was born on|born date:)\s*.*?(\d{4})", profile_str, re.IGNORECASE)
            if born_match:
                person_data['birth_year'] = int(born_match.group(1))
            else:
                person_data['birth_year'] = None

            if person_data.get('name'):
                structured_profiles.append(person_data)

        return structured_profiles

    except Exception as e:
        st.error(f"Critical error while parsing the document: {e}")
        return []

# --- Improved Age Ranking ---
def rank_by_age(profiles):
    available = [p for p in profiles if p.get('birth_year')]
    missing = [p for p in profiles if not p.get('birth_year')]

    if not available:
        return "⚠️ No valid birth years found."

    sorted_members = sorted(available, key=lambda x: x['birth_year'])  # oldest first

    result = []
    for member in sorted_members:
        age = datetime.now().year - member['birth_year']
        result.append(f"- **{member['alias']}** (Born {member['birth_year']}, approx. {age} years old)")

    if missing:
        result.append("\n⚠️ Birth year not available for: " + ", ".join(m['alias'] for m in missing))

    return "\n".join(result)

# --- Stronger Search with Fuzzy Matching ---
def search_profiles(profiles, query, threshold=60):
    results = []
    for p in profiles:
        score = fuzz.partial_ratio(query.lower(), p['full_text'].lower())
        if score >= threshold:
            results.append((score, p))
    results.sort(reverse=True, key=lambda x: x[0])
    return [p for _, p in results]

# --- Analyst Brain ---
def handle_analytical_question(prompt, profiles):
    prompt_lower = prompt.lower()
    target_group_keyword = "family member"  # Default

    known_groups = list(profession_keywords.keys()) + ["family member"]
    for group in known_groups:
        if group in prompt_lower:
            target_group_keyword = group
            break

    if any(keyword in prompt_lower for keyword in ["rank", "list", "oldest", "youngest", "how many"]):
        # Filter members
        if target_group_keyword == "family member":
            group_members = [p for p in profiles if p.get('birth_year')]
        else:
            group_members = [
                p for p in profiles
                if detect_profession(p['full_text'], target_group_keyword) and p.get('birth_year')
            ]

        if not group_members:
            return f"I couldn't find anyone in the '{target_group_keyword}' category with enough data."

        # Handle "how many"
        if "how many" in prompt_lower:
            return f"There are **{len(group_members)}** members in the '{target_group_keyword}' category that I can identify."

        # Handle sorting/ranking
        return rank_by_age(group_members)

    return None

# --- Main Application Logic ---
structured_family_data = parse_family_document()

if structured_family_data:
    if prompt := st.chat_input("Ask a question about our family..."):
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            analytical_answer = handle_analytical_question(prompt, structured_family_data)

            if analytical_answer:
                st.markdown(analytical_answer)
            else:
                # Fallback: Creative Brain
                with st.spinner("Let me think of a good story..."):
                    mentioned_names = re.findall(r'\b[A-Z][a-z]+\b', prompt)
                    relevant_profiles_text = [
                        p['full_text'] for p in structured_family_data
                        if any(name.lower() in p['name'].lower() for name in mentioned_names)
                    ] if mentioned_names else [p['full_text'] for p in structured_family_data[:5]]

                    context = "\n\n--- PERSON START ---\n".join(relevant_profiles_text)

                    system_prompt = {
                        "role": "system",
                        "content": f"""You are a witty, charming, and humorous AI assistant for the Gupta family. 
                        Answer questions based ONLY on the provided context. 
                        ALWAYS refer to people by their alias. Be diplomatic for subjective questions.

                        Relevant Context:
                        ---
                        {context}
                        ---
                        """
                    }

                    messages_for_api = [system_prompt, {"role": "user", "content": prompt}]

                    try:
                        chat_completion = client.chat.completions.create(
                            messages=messages_for_api,
                            model="llama-3.3-70b-versatile",
                            temperature=0.75,
                            max_tokens=1024
                        )
                        response = chat_completion.choices[0].message.content
                        st.markdown(response)
                    except Exception as e:
                        st.error(f"Failed to get a response from the AI. Error: {e}")
