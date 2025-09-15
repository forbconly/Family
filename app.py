import streamlit as st
from groq import Groq
import docx
import re
from datetime import datetime

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
Ask me to 'rank the engineers by age' or ask something creative like 'Tell me a funny story about someone'.
""")

# --- Groq API Client Initialization ---
try:
    groq_api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=groq_api_key)
except Exception:
    st.error("Groq API key not found! Please add it to your Streamlit secrets.")
    st.stop()

# --- Data Parsing and Structuring ---
@st.cache_data(show_spinner="Reading and analyzing the family chronicles...")
def parse_family_document(file_path="Family.docx"):
    """
    Reads the .docx file and parses it into a list of structured dictionaries.
    This is the core of our new 'Analyst' brain.
    """
    try:
        doc = docx.Document(file_path)
        full_text = "\n".join([para.text for para in doc.paragraphs])
        profiles_text = full_text.split("--- PERSON START ---")[1:]
        
        structured_profiles = []
        for profile_str in profiles_text:
            person_data = {'full_text': profile_str.strip()}
            
            # Extract Name and Alias
            name_match = re.search(r"Name:\s*(.*?)\s*\(alias\s*(.*?)\)", profile_str)
            if name_match:
                person_data['name'] = name_match.group(1).strip()
                person_data['alias'] = name_match.group(2).strip()
            else:
                name_match_simple = re.search(r"Name:\s*(.*)", profile_str)
                if name_match_simple:
                    person_data['name'] = name_match_simple.group(1).strip()
                    person_data['alias'] = person_data['name'].split()[0] # Default alias to first name

            # Extract Birth Year/Date
            born_match = re.search(r"Born:\s*.*?(\d{4})", profile_str)
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

# --- "Analyst Brain" for Factual Questions ---
def handle_ranking_question(prompt, profiles):
    """
    Handles data-driven questions like ranking and listing.
    Returns a formatted string response if the question is a match, otherwise None.
    """
    prompt_lower = prompt.lower()
    
    # Target keyword for ranking: 'engineer', 'doctor', etc.
    target_group = None
    if "engineer" in prompt_lower:
        target_group = "engineer"
    elif "doctor" in prompt_lower:
        target_group = "doctor"

    if ("rank" in prompt_lower or "list" in prompt_lower or "oldest" in prompt_lower or "youngest" in prompt_lower) and target_group:
        
        # 1. Filter for the target group
        group_members = [
            p for p in profiles 
            if target_group in p['full_text'].lower() and p['birth_year'] is not None
        ]
        
        if not group_members:
            return f"I couldn't find any members of the '{target_group}' group with a recorded birth year to rank."

        # 2. Sort them
        sort_order = "youngest" in prompt_lower
        sorted_members = sorted(group_members, key=lambda x: x['birth_year'], reverse=sort_order)
        
        # 3. Format the response
        response = f"Of course! Here is a ranking of the family's **{target_group}s** by age:\n"
        rank_list = []
        for member in sorted_members:
            age = datetime.now().year - member['birth_year']
            rank_list.append(f"- **{member['alias']}** (Born {member['birth_year']}, approx. {age} years old)")
        
        return "\n".join([response] + rank_list)
        
    return None # Indicates this function couldn't handle the prompt

# --- Main Application Logic ---
structured_family_data = parse_family_document()

if structured_family_data:
    if prompt := st.chat_input("Ask a question about our family..."):
        with st.chat_message("user"):
            st.markdown(prompt)

        # --- Intelligent Question Routing ---
        with st.chat_message("assistant"):
            # First, try the Analyst Brain for factual questions
            factual_answer = handle_ranking_question(prompt, structured_family_data)
            
            if factual_answer:
                st.markdown(factual_answer)
            else:
                # If it's not a factual question, use the Creative AI Brain (RAG)
                with st.spinner("Let me think of a good story..."):
                    # Simple retrieval: find profiles matching any capitalized name in the prompt
                    mentioned_names = re.findall(r'\b[A-Z][a-z]+\b', prompt)
                    relevant_profiles_text = [
                        p['full_text'] for p in structured_family_data 
                        if any(name.lower() in p['name'].lower() for name in mentioned_names)
                    ]
                    if not relevant_profiles_text: # Fallback if no names mentioned
                        relevant_profiles_text = [p['full_text'] for p in structured_family_data[:3]]
                    
                    context = "\n\n--- PERSON START ---\n".join(relevant_profiles_text)
                    
                    system_prompt = {
                        "role": "system",
                        "content": f"""You are a witty, charming, and humorous AI assistant for the Gupta family. 
                        Your personality is that of a fun family insider who loves telling stories.
                        You must answer questions based ONLY on the provided context below.
                        ALWAYS refer to people by their pet name (alias). Be diplomatic about subjective questions.

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
                            model="openai/gpt-oss-120b",
                            temperature=0.75, max_tokens=1024
                        )
                        response = chat_completion.choices[0].message.content
                        st.markdown(response)
                    except Exception as e:
                        st.error(f"Failed to get a response from the AI. Error: {e}")

