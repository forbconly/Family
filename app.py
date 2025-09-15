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
            name_match = re.search(r"Name:\s*(.*?)\s*\(alias\s*(.*?)\)", profile_str, re.IGNORECASE)
            if name_match:
                person_data['name'] = name_match.group(1).strip()
                person_data['alias'] = name_match.group(2).strip()
            else:
                name_match_simple = re.search(r"Name:\s*(.*)", profile_str, re.IGNORECASE)
                if name_match_simple:
                    person_data['name'] = name_match_simple.group(1).strip()
                    person_data['alias'] = person_data['name'].split()[0]

            # *** THE KEY FIX IS HERE: A much more flexible date finder ***
            # It now looks for multiple patterns like "Born on", "Born in year", "was born on", etc.
            born_match = re.search(r"(?:born on|born in year|born in|was born on|born date:)\s*.*?(\d{4})", profile_str, re.IGNORECASE)
            if born_match:
                person_data['birth_year'] = int(born_match.group(1))
            else:
                person_data['birth_year'] = None # Explicitly set to None if not found

            if person_data.get('name'):
                structured_profiles.append(person_data)
        
        return structured_profiles

    except Exception as e:
        st.error(f"Critical error while parsing the document: {e}")
        return []

# --- "Analyst Brain" for Factual Questions ---
def handle_analytical_question(prompt, profiles):
    """
    Handles data-driven questions like ranking, listing, and counting.
    Returns a formatted string response if the question is a match, otherwise None.
    """
    prompt_lower = prompt.lower()
    
    # Identify the target group (e.g., 'engineer', 'doctor', 'family member')
    target_group_keyword = "family member" # Default
    known_groups = ['engineer', 'doctor', 'iitian', 'lawyer', 'ca']
    for group in known_groups:
        if group in prompt_lower:
            target_group_keyword = group
            break

    # Check for analytical keywords
    if any(keyword in prompt_lower for keyword in ["rank", "list", "oldest", "youngest", "how many"]):
        
        # Filter for the target group
        if target_group_keyword == "family member":
            group_members = [p for p in profiles if p.get('birth_year')]
        else:
            group_members = [
                p for p in profiles 
                if target_group_keyword in p['full_text'].lower() and p.get('birth_year')
            ]
        
        if not group_members:
            return f"I couldn't find anyone in the '{target_group_keyword}' category with a recorded birth year to create a list."

        # Handle "how many"
        if "how many" in prompt_lower:
            return f"There are **{len(group_members)}** members in the '{target_group_keyword}' category that I can identify."

        # Handle sorting
        sort_order_reverse = "oldest" in prompt_lower or "rank" in prompt_lower
        sorted_members = sorted(group_members, key=lambda x: x['birth_year'], reverse=sort_order_reverse)
        
        # Format the response
        title = f"Here is a list of the family's **{target_group_keyword}s**, ranked by age:" if "rank" in prompt_lower else "Here is the list you requested:"
        rank_list = [title]
        for member in sorted_members:
            age = datetime.now().year - member['birth_year']
            rank_list.append(f"- **{member['alias']}** (Born {member['birth_year']}, approx. {age} years old)")
        
        return "\n".join(rank_list)
        
    return None # Indicates this function couldn't handle the prompt

# --- Main Application Logic ---
structured_family_data = parse_family_document()

if structured_family_data:
    if prompt := st.chat_input("Ask a question about our family..."):
        with st.chat_message("user"):
            st.markdown(prompt)

        # --- Intelligent Question Routing ---
        with st.chat_message("assistant"):
            analytical_answer = handle_analytical_question(prompt, structured_family_data)
            
            if analytical_answer:
                st.markdown(analytical_answer)
            else:
                # Fallback to the Creative AI Brain (RAG) for narrative questions
                with st.spinner("Let me think of a good story..."):
                    # Simple retrieval: find profiles matching any capitalized name in the prompt
                    mentioned_names = re.findall(r'\b[A-Z][a-z]+\b', prompt)
                    relevant_profiles_text = [
                        p['full_text'] for p in structured_family_data 
                        if any(name.lower() in p['name'].lower() for name in mentioned_names)
                    ] if mentioned_names else [p['full_text'] for p in structured_family_data[:5]] # Fallback
                    
                    context = "\n\n--- PERSON START ---\n".join(relevant_profiles_text)
                    
                    system_prompt = { "role": "system", "content": f"""You are a witty, charming, and humorous AI assistant for the Gupta family. Your personality is that of a fun family insider who loves telling stories. You must answer questions based ONLY on the provided context below. ALWAYS refer to people by their pet name (alias). Be diplomatic about subjective questions.

                    Relevant Context:
                    ---
                    {context}
                    ---
                    """}
                    
                    messages_for_api = [system_prompt, {"role": "user", "content": prompt}]
                    
                    try:
                        chat_completion = client.chat.completions.create(
                            messages=messages_for_api,
                            # Using a larger, more capable model as requested
                            model="llama3-70b-8192", 
                            temperature=0.75, max_tokens=1024
                        )
                        response = chat_completion.choices[0].message.content
                        st.markdown(response)
                    except Exception as e:
                        st.error(f"Failed to get a response from the AI. Error: {e}")

