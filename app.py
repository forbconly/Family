import streamlit as st
import os
import re
import random
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()

# --- UI Text Translations ---
# Central dictionary for handling English and Hindi translations
UI_TEXT = {
    "English 🇬🇧": {
        "page_title": "Family AI",
        "app_title": "🤖 Aaradhana Family AI",
        "next_event_header": "🗓️ Next Event: ",
        "today": "is today!",
        "tomorrow": "is tomorrow!",
        "in_days": "is in {days} days",
        "birthday": "birthday",
        "anniversary": "anniversary",
        "years": "years",
        "chat_tab": "💬 Chatbot",
        "chat_welcome": "Ask me anything about the family! Like, Who is the Bullet Raja of the family?",
        "chat_input_placeholder": "What do you want to know?",
        "thinking": "Thinking...",
        "trivia_tab": "🏆 Family Trivia Game",
        "trivia_header": "How well do you know the family?",
        "trivia_button": "Start New Game / Next Question",
        "trivia_form_header": "Choose your answer:",
        "trivia_submit": "Submit Answer",
        "trivia_correct": "Correct! You're a family expert!",
        "trivia_incorrect": "Not quite! The correct answer was: {answer}"
    },
    "Hindi 🇮🇳": {
        "page_title": "फैमिली एआई",
        "app_title": "🤖 आराधना फैमिली AI",
        "next_event_header": "🗓️ अगला कार्यक्रम: ",
        "today": "आज है!",
        "tomorrow": "कल है!",
        "in_days": "{days} दिनों में है",
        "birthday": "जन्मदिन",
        "anniversary": "सालगिरह",
        "years": "साल",
        "chat_tab": "💬 चैटबॉट",
        "chat_welcome": "परिवार के बारे में कुछ भी पूछें! जैसे, परिवार का बुलेट राजा कौन है?",
        "chat_input_placeholder": "आप क्या जानना चाहते हैं?",
        "thinking": "सोच रहा हूँ...",
        "trivia_tab": "🏆 पारिवारिक सामान्य ज्ञान",
        "trivia_header": "आप परिवार को कितना जानते हैं?",
        "trivia_button": "नया गेम शुरू करें / अगला प्रश्न",
        "trivia_form_header": "अपना उत्तर चुनें:",
        "trivia_submit": "उत्तर सबमिट करें",
        "trivia_correct": "सही! आप एक पारिवारिक विशेषज्ञ हैं!",
        "trivia_incorrect": "सही नहीं! सही उत्तर था: {answer}"
    }
}

# --- Helper Functions ---
def load_family_data(filepath="family_data.md"):
    """Loads family data from a markdown file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.error(f"Error: The data file '{filepath}' was not found.")
        st.info("Please make sure you have a `family_data.md` file in the same directory.")
        st.stop()
        return None

# --- Feature Functions ---
def get_next_event_message(family_data, lang_text):
    """
    Parses the family data to find the next upcoming birthday or anniversary.
    """
    today_date = datetime.now().date()
    next_event = None
    smallest_delta = timedelta(days=367) # Initialize with a value larger than a year

    # Regex to find all person data blocks, ignoring case for end marker
    person_blocks = re.findall(r'---Person Start---(.*?)---Person Ends?---', family_data, re.DOTALL | re.IGNORECASE)
    
    for block in person_blocks:
        name_match = re.search(r'Name:\s*(.*)', block)
        if not name_match:
            continue
        name = name_match.group(1).strip()
        
        event_types = [
            ("Born", lang_text["birthday"]),
            ("Anniversary", lang_text["anniversary"])
        ]
        
        for tag, event_name in event_types:
            # More specific regex to find dates like "Month Day, Year" or "Month Day"
            date_match = re.search(fr'{tag}:\s*([A-Za-z]+\s\d{{1,2}}(?:,\s*\d{{4}})?)\s*$', block, re.MULTILINE)
            if date_match:
                date_str = date_match.group(1).strip().replace(',', '')
                event_date = None
                has_year = False
                
                # Try parsing with year first, then without
                try:
                    event_date = datetime.strptime(date_str, '%B %d %Y')
                    has_year = True
                except ValueError:
                    try:
                        # Use a placeholder year for events without one, makes calculation easier
                        event_date = datetime.strptime(date_str + " 1900", '%B %d %Y')
                    except ValueError:
                        # Skip if date format is invalid
                        continue
                
                # Determine the next occurrence of this event
                next_occurrence_dt = event_date.replace(year=today_date.year)
                if next_occurrence_dt.date() < today_date:
                    next_occurrence_dt = next_occurrence_dt.replace(year=today_date.year + 1)
                
                delta = next_occurrence_dt.date() - today_date
                
                if 0 <= delta.days < smallest_delta.days:
                    smallest_delta = delta
                    year_diff = next_occurrence_dt.year - event_date.year if has_year else None
                    next_event = {
                        "name": name,
                        "year_diff": year_diff,
                        "date": next_occurrence_dt,
                        "delta": delta,
                        "type": event_name
                    }

    if not next_event:
        return ""
    
    event_date_str = next_event['date'].strftime('%B %d')
    delta_days = next_event['delta'].days
    
    if delta_days == 0:
        day_info = lang_text["today"]
    elif delta_days == 1:
        day_info = lang_text["tomorrow"]
    else:
        day_info = lang_text["in_days"].format(days=delta_days)
    
    event_details = ""
    if next_event['year_diff'] is not None:
        if next_event['type'] == lang_text["birthday"]:
            event_details = f"({next_event['year_diff']})"
        else:
            event_details = f"({next_event['year_diff']} {lang_text['years']})"
            
    return (f"{lang_text['next_event_header']}**{next_event['name']}'s** {next_event['type']} {event_details} "
            f"{day_info} on **{event_date_str}**.")


def parse_data_for_quiz(family_data):
    """Parses facts from the family data to be used in the trivia quiz."""
    facts = []
    person_blocks = re.findall(r'---Person Start---(.*?)---Person Ends?---', family_data, re.DOTALL | re.IGNORECASE)
    for block in person_blocks:
        name_match = re.search(r'Name:\s*(.*)', block)
        if name_match:
            name = name_match.group(1).strip()
            # Find all lines that are not empty and don't match the standard fields
            fact_matches = re.findall(r'(\w[\w\s]+):\s*(.*)', block)
            for fact_type, fact_value in fact_matches:
                # Exclude structural or date fields from being "facts"
                if fact_type.strip() not in ["Name", "Born", "Anniversary"]:
                    facts.append({"person": name, "fact_type": fact_type.strip(), "fact_value": fact_value.strip()})
    return facts

def generate_quiz_question(facts, lang_text):
    """Generates a single quiz question with multiple choice options."""
    if len(facts) < 3:
        return None # Not enough facts to create a meaningful question

    correct_fact = random.choice(facts)
    
    # Define question templates for both languages
    question_templates = {
        "English 🇬🇧": "Regarding {person}, what is one of their '{fact_type}'?",
        "Hindi 🇮🇳": "{person} के बारे में, उनकी एक '{fact_type}' क्या है?"
    }
    
    question = question_templates[language].format(
        person=correct_fact['person'],
        fact_type=correct_fact['fact_type']
    )
    
    correct_answer = correct_fact['fact_value']
    
    # Create a pool of potential incorrect answers from different people or fact types
    incorrect_options_pool = [f['fact_value'] for f in facts if f['fact_value'] != correct_answer]
    
    if len(incorrect_options_pool) < 2:
        return None # Not enough variety for incorrect options

    incorrect_answers = random.sample(incorrect_options_pool, 2)
    options = [correct_answer] + incorrect_answers
    random.shuffle(options)
    
    return {"question": question, "options": options, "correct_answer": correct_answer}

def get_ai_response(client, messages, model):
    """Gets a response from the AI model."""
    try:
        chat_completion = client.chat.completions.create(
            messages=messages,
            model=model
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        st.error(f"An error occurred while contacting the AI model: {e}")
        return None

# --- Streamlit App ---

# Set page configuration
st.set_page_config(page_title="Family AI", page_icon="👨‍👩‍👧‍👦")

# Sidebar for settings
st.sidebar.title("Settings")
language = st.sidebar.radio("Choose language | भाषा चुनें", list(UI_TEXT.keys()))
lang_text = UI_TEXT[language]

# Main title
st.title(lang_text["app_title"])

# Load data and AI model configuration
family_data = load_family_data()
# Make the model configurable via environment variables for flexibility.
# Switched default model to one less likely to have data policy issues on OpenRouter.
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3-70b-instruct")

try:
    # Use st.secrets for deployed apps, fallback to os.environ for local
    openrouter_api_key = st.secrets.get("OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY"))
    if not openrouter_api_key:
        raise KeyError
    
    client = OpenAI(
      base_url="https://openrouter.ai/api/v1",
      api_key=openrouter_api_key,
    )
except KeyError:
    st.error("OPENROUTER_API_KEY not found! Please set it in your .env file or Streamlit Secrets.")
    st.stop()

# Display the next event message
next_event_msg = get_next_event_message(family_data, lang_text)
if next_event_msg:
    st.info(next_event_msg)

# Create tabs for Chatbot and Trivia
tab1, tab2 = st.tabs([lang_text["chat_tab"], lang_text["trivia_tab"]])

# --- Chatbot Tab ---
with tab1:
    st.write(lang_text["chat_welcome"])
    
    # Initialize or reset chat state if language changes
    if "messages" not in st.session_state or st.session_state.get("language") != language:
        st.session_state.language = language
        if language == "English 🇬🇧":
            system_prompt = f"""You are a witty, creative, and respectful AI assistant for a family. Your name is 'FamBot'. 
Your strict rules are: be funny, respectful, diplomatic, and always add a fun fact. 
Base all your answers strictly on the following Family Knowledge Base.
---
Family Knowledge Base:
{family_data}
---"""
        else: # Hindi
            system_prompt = f"""आप परिवार के लिए एक मजाकिया, रचनात्मक और सम्मानजनक एआई सहायक हैं। आपका नाम 'FamBot' है। आपका पूरा वार्तालाप हिंदी में होना चाहिए।
आपके सख्त नियम हैं:
1. पहले, दिए गए ज्ञान के आधार पर उपयोगकर्ता के प्रश्न का सीधे उत्तर दें।
2. उत्तर के बाद, हमेशा एक संबंधित, रचनात्मक "रोचक तथ्य" (fun fact) जोड़ें।
3. व्यक्तिपरक प्रश्नों के लिए (जैसे "सबसे बुद्धिमान कौन है?"), आपको कूटनीतिक होना चाहिए।
4. आपका लहजा मजाकिया, आकर्षक और हमेशा सम्मानजनक होना चाहिए।
5. अपने सभी उत्तर केवल निम्नलिखित पारिवारिक ज्ञान के आधार पर दें।
---
पारिवारिक ज्ञान:
{family_data}
---"""
        st.session_state.messages = [{"role": "system", "content": system_prompt}]

    # Display past messages
    for message in st.session_state.messages:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Handle new user input
    if prompt := st.chat_input(lang_text["chat_input_placeholder"]):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner(lang_text["thinking"]):
                response = get_ai_response(client, st.session_state.messages, OPENROUTER_MODEL)
                if response:
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

# --- Family Trivia Tab ---
with tab2:
    st.header(lang_text["trivia_header"])
    
    # Initialize quiz facts if they don't exist in the session state
    if 'quiz_facts' not in st.session_state:
        st.session_state.quiz_facts = parse_data_for_quiz(family_data)
        
    if st.button(lang_text["trivia_button"]):
        st.session_state.quiz_question = generate_quiz_question(st.session_state.quiz_facts, lang_text)
        st.session_state.answered = False # Reset answered state for new question

    if 'quiz_question' in st.session_state and st.session_state.quiz_question:
        q = st.session_state.quiz_question
        st.subheader(q['question'])
        
        with st.form("quiz_form"):
            selected_option = st.radio(lang_text["trivia_form_header"], q['options'], key="quiz_options")
            submitted = st.form_submit_button(lang_text["trivia_submit"])
            
            if submitted and not st.session_state.get('answered', False):
                st.session_state.answered = True
                if selected_option == q['correct_answer']:
                    st.success(lang_text["trivia_correct"])
                else:
                    st.error(lang_text["trivia_incorrect"].format(answer=q['correct_answer']))

