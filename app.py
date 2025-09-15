import streamlit as st
from groq import Groq
import docx

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
Ask me anything from 'Tell me a funny story about Hamir Mal's bullet motorcycle' to 'Who is the youngest in the family?'.
I'll do my best to answer with a bit of humor and fun!
""")

# --- Groq API Client Initialization ---
try:
    groq_api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=groq_api_key)
except Exception:
    st.error("Groq API key not found! Please add it to your Streamlit secrets.")
    st.stop()

# --- Data Loading Function ---
@st.cache_data(show_spinner="Reading the family chronicles...")
def load_family_data(file_path="Family.docx"):
    """
    Loads text from a .docx file.
    The @st.cache_data decorator ensures this function only runs once.
    """
    try:
        doc = docx.Document(file_path)
        full_text = [para.text for para in doc.paragraphs]
        return "\n".join(full_text)
    except FileNotFoundError:
        st.error(f"Error: The file '{file_path}' was not found. Please make sure it's uploaded to your GitHub repository.")
        return None
    except Exception as e:
        st.error(f"An error occurred while reading the document: {e}")
        return None

# --- Main Application Logic ---
family_info = load_family_data()

if family_info:
    if prompt := st.chat_input("Ask a question about our family..."):
        with st.chat_message("user"):
            st.markdown(prompt)

        # --- FINAL, REVISED SYSTEM PROMPT ---
        system_prompt = {
            "role": "system",
            "content": """You are a witty, charming, and humorous AI assistant for the Gupta family. 
            Your personality is that of a fun family insider who loves telling stories.
            You must answer questions based ONLY on the provided, highly-structured family history document.

            **Core Rules:**
            1.  **Strict Data Adherence:** The provided document uses "--- PERSON START ---" and "--- PERSON END ---" to separate entries. Treat each block as a unique record. Do NOT mix facts between different blocks.

            2.  **Prioritize Pet Names (Aliases):** This is your most important rule for tone. The data is structured as `Name: Official Name (alias Pet Name)`. To keep things informal and loving, ALWAYS refer to people by their pet name (the 'alias') if one is provided. For example, instead of 'Laxmi', call her 'Munni'. Instead of 'Vineet', call him 'Vicky'.

            3.  **Handle Comparative Questions Diplomatically:** If asked a subjective or comparative question (e.g., "Who is the smartest?", "Who is the most beautiful?"), you MUST NOT pick one person. Instead, give a diplomatic answer that celebrates everyone. For example, for "Who is the most intelligent?", you could say: "That's a tough one! Our family is full of brilliant people in their own ways. We have accomplished IITians like Vicky and Pikul, skilled doctors like Hemant, and seasoned professionals like Ashish. Everyone's intelligence shines in different areas!"

            4.  **Use Indian Relationship Terms:** The family is Indian. When asked about relationships, use specific terms if possible. For example, instead of just "aunt," specify if she is a 'Bua' (father's sister) or 'Masi' (mother's sister). Infer this from the family structure provided in the document.

            5.  **Friendly Persona:** Be creative, friendly, and humorous. Embellish stories based on personality traits, but never be insulting. Keep the tone light and positive.

            6.  **Handle Missing Information:** If the information is not in the document, say something like "That's a great question! Unfortunately, that story isn't in my memory banks yet."

            Here is the family history document:
            ---
            """ + family_info + """
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
                with st.spinner("Checking the family album..."):
                    chat_completion = client.chat.completions.create(
                        messages=messages_for_api,
                        model="openai/gpt-oss-120b",
                        temperature=0.75, # Slightly increased for more creative/natural language
                        max_tokens=1024,
                        top_p=1,
                        stream=False,
                    )
                    response = chat_completion.choices[0].message.content
                    st.markdown(response)
        except Exception as e:
            st.error(f"Failed to get a response from the AI. Error: {e}")

