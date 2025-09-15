import streamlit as st
from groq import Groq
import docx
import re

# --- Page Configuration ---
st.set_page_config(
    page_title="The Gupta Family AI",
    page_icon="👨‍👩‍👧‍👦",
    layout="centered"
)

# --- UI Title and Description ---
st.title("👨‍👩‍👧‍👦 The Gupta Family AI Assistant")
st.markdown("""
Welcome! I'm your personal AI assistant, trained on our family's history. 
This new version is smarter and faster! Ask me anything.
""")

# --- Groq API Client Initialization ---
try:
    groq_api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=groq_api_key)
except Exception:
    st.error("Groq API key not found! Please add it to your Streamlit secrets.")
    st.stop()

# --- Data Processing Functions ---
@st.cache_data(show_spinner="Reading and organizing the family chronicles...")
def process_family_document(file_path="Family.docx"):
    """
    Loads text from a .docx file and splits it into individual person profiles.
    """
    try:
        doc = docx.Document(file_path)
        full_text = "\n".join([para.text for para in doc.paragraphs])
        profiles = full_text.split("--- PERSON START ---")
        cleaned_profiles = [profile.strip() for profile in profiles if profile.strip()]
        return cleaned_profiles
    except FileNotFoundError:
        st.error(f"Error: The file '{file_path}' was not found. Please make sure it's uploaded to your GitHub repository.")
        return []
    except Exception as e:
        st.error(f"An error occurred while reading the document: {e}")
        return []

def find_relevant_profiles_smart(user_prompt, profiles):
    """
    An improved retrieval function that understands topics and synonyms.
    This function now performs a two-pass search:
    1. Topical Search: Looks for keywords related to professions or topics.
    2. Name-based Search: Looks for specific names mentioned in the prompt.
    """
    prompt_lower = user_prompt.lower()
    found_profiles = set()

    # --- Pass 1: Topical and Synonym Search ---
    # We define keywords for important topics. This can be expanded.
    topic_keywords = {
        'doctor': ['doctor', 'doctors', 'mbbs', 'medicine', 'cardiologist'],
        'engineer': ['engineer', 'engineers', 'iit', 'm.tech'],
        'law': ['law', 'lawyer', 'judge'],
        'business': ['business', 'startup', 'entrepreneur', 'bank', 'banker', 'chartered accountant'],
        'travel': ['travel', 'travelled', 'countries', 'trip', 'tours']
    }

    # Check if any of the prompt keywords match our topic list
    for topic, synonyms in topic_keywords.items():
        if any(synonym in prompt_lower for synonym in synonyms):
            # If a topic is matched, find all profiles containing any of the synonyms
            for profile in profiles:
                profile_lower = profile.lower()
                if any(synonym in profile_lower for synonym in synonyms):
                    found_profiles.add(profile)

    # --- Pass 2: Name-based Search ---
    # Extracts capitalized words (likely names) from the prompt
    mentioned_names = re.findall(r'\b[A-Z][a-z]+\b', user_prompt)
    for name in mentioned_names:
        name_lower = name.lower()
        for profile in profiles:
            # Check if the name appears near the 'Name:' field for accuracy
            if f"name: {name_lower}" in profile.lower() or f"(alias {name_lower})" in profile.lower():
                 found_profiles.add(profile)

    # If after all searches, no profiles are found, return a default set (e.g., first 2)
    if not found_profiles:
        return profiles[:2] # Fallback to prevent sending an empty context

    return list(found_profiles)


# --- Main Application Logic ---
all_profiles = process_family_document()

if all_profiles:
    if prompt := st.chat_input("Ask a question about our family..."):
        with st.chat_message("user"):
            st.markdown(prompt)

        # --- STEP 1: RETRIEVAL (Using the new smart function) ---
        with st.spinner("Searching for the right story..."):
            relevant_context_list = find_relevant_profiles_smart(prompt, all_profiles)
            relevant_context = "\n\n--- PERSON START ---\n".join(relevant_context_list)
        
        # --- STEP 2: GENERATION ---
        system_prompt = {
            "role": "system",
            "content": """You are a witty, charming, and humorous AI assistant for the Gupta family. 
            Your personality is that of a fun family insider who loves telling stories.
            You will be given a user's question and a SMALL, RELEVANT SUBSET of the family history.
            You must answer questions based ONLY on this provided subset of information.

            **Core Rules:**
            1.  **Use Only Provided Context:** Do not use any information outside of the text I provide below.
            2.  **Prioritize Pet Names (Aliases):** ALWAYS refer to people by their pet name (the 'alias') if one is provided. E.g., call 'Laxmi' 'Munni', and 'Vineet' 'Vicky'. This is crucial for a friendly tone.
            3.  **Handle Comparative Questions Diplomatically:** If asked a subjective question (e.g., "Who is the smartest?"), DO NOT pick one person. Give a diplomatic answer celebrating everyone mentioned in the context.
            4.  **Use Indian Relationship Terms:** Use specific terms like 'Bua', 'Masi', 'Mama' if they are mentioned in the provided context.
            5.  **Handle Missing Information:** If the answer is not in the provided context, say something like "That's a great question! I couldn't find that detail in the stories I just looked at."

            Here is the relevant information for the current question:
            ---
            """ + relevant_context + """
            ---
            """
        }
        
        messages_for_api = [
            system_prompt,
            {"role": "user", "content": prompt}
        ]

        try:
            with st.chat_message("assistant"):
                with st.spinner("Crafting a reply..."):
                    chat_completion = client.chat.completions.create(
                        messages=messages_for_api,
                        model="openai/gpt-oss-120b",
                        temperature=0.75,
                        max_tokens=1024,
                        top_p=1,
                        stream=False,
                    )
                    response = chat_completion.choices[0].message.content
                    st.markdown(response)
        except Exception as e:
            st.error(f"Failed to get a response from the AI. Error: {e}")

