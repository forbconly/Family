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
    This is the core of our retrieval system.
    """
    try:
        doc = docx.Document(file_path)
        full_text = "\n".join([para.text for para in doc.paragraphs])
        # Split the text into profiles using the '--- PERSON START ---' delimiter
        profiles = full_text.split("--- PERSON START ---")
        # Clean up profiles: remove empty strings and leading/trailing whitespace
        cleaned_profiles = [profile.strip() for profile in profiles if profile.strip()]
        return cleaned_profiles
    except FileNotFoundError:
        st.error(f"Error: The file '{file_path}' was not found. Please make sure it's uploaded to your GitHub repository.")
        return []
    except Exception as e:
        st.error(f"An error occurred while reading the document: {e}")
        return []

def find_relevant_profiles(user_prompt, profiles, max_profiles=5):
    """
    Finds the most relevant person profiles based on the user's prompt.
    This is a simple but effective keyword-based retrieval method.
    """
    relevant_profiles = []
    
    # Extract potential names/keywords from the prompt.
    # We look for capitalized words as they are likely names.
    keywords = set([word.lower() for word in re.findall(r'\b[A-Z][a-zA-Z]*\b', user_prompt)] + user_prompt.lower().split())

    for profile in profiles:
        profile_lower = profile.lower()
        # Score profiles based on how many keywords they contain
        score = sum(1 for keyword in keywords if keyword in profile_lower)
        
        if score > 0:
            relevant_profiles.append({"profile": profile, "score": score})

    # Sort profiles by score in descending order and take the top ones
    sorted_profiles = sorted(relevant_profiles, key=lambda x: x["score"], reverse=True)
    
    # Return the text of the top N profiles
    return [item["profile"] for item in sorted_profiles[:max_profiles]]

# --- Main Application Logic ---
all_profiles = process_family_document()

if all_profiles:
    if prompt := st.chat_input("Ask a question about our family..."):
        with st.chat_message("user"):
            st.markdown(prompt)

        # --- STEP 1: RETRIEVAL ---
        with st.spinner("Searching for the right story..."):
            relevant_context_list = find_relevant_profiles(prompt, all_profiles)
            if not relevant_context_list:
                # If no specific person is found, maybe provide a general context
                # For simplicity now, we'll just use the first profile (head of family)
                relevant_context_list.append(all_profiles[0])
            
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

        # Call the Groq API
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

