import streamlit as st
import os
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Functions ---

def load_family_data(filepath="family_data.md"):
    """Reads the family data from the specified file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Error: Family data file not found. Please make sure 'family_data.md' is in the same folder."

def get_groq_response(client, user_query, family_info):
    """Gets a response from the Groq API based on the user's query and family data."""
    system_prompt = f"""
    You are a witty, creative, and respectful AI assistant for a family. Your name is 'FamBot'.
    Your goal is to answer questions about the family using the provided data.
    
    **Your strict rules are:**
    1.  **Answer Directly:** First, directly answer the user's question based on the knowledge base below.
    2.  **Add a Fun Fact:** After the answer, ALWAYS add a related, creative "fun fact" or a witty observation.
    3.  **Be Diplomatic:** For subjective questions (like "who is the smartest?" or "who is the best?"), you MUST be diplomatic. Do not pick one person. Instead, highlight the positive traits of several people in a funny or clever way.
    4.  **Tone:** Your tone must be funny, charming, and always respectful. Never say anything negative or insulting.
    5.  **Use Provided Data Only:** Base all your answers strictly on the following family knowledge base. If the answer isn't in the data, politely say you don't have that information.

    ---
    **Family Knowledge Base:**
    {family_info}
    ---
    """
    
    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": user_query
        }
    ]

    try:
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"An error occurred with the API: {e}"

# --- Streamlit App ---

# Set up the Streamlit page
st.set_page_config(page_title="Family Chatbot", page_icon="👨‍👩‍👧‍👦")
st.title("🤖 The Family AI Chatbot")
st.write("Ask me anything about the family!")

# Load data and initialize Groq client
family_data = load_family_data()
try:
    groq_api_key = os.environ['GROQ_API_KEY']
    client = Groq(api_key=groq_api_key)
except KeyError:
    st.error("GROQ_API_KEY not found! Please make sure it's set in your .env file.")
    st.stop()

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display prior chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle user input
if prompt := st.chat_input("What do you want to know?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get and display assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = get_groq_response(client, prompt, family_data)
            st.markdown(response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
