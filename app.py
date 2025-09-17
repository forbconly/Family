import streamlit as st
import os
import re
import random
from datetime import datetime, timedelta
from openai import OpenAI # MODIFIED: Import OpenAI instead of Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- UI Text Translations (No Change) ---
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
        "chat_welcome": "Ask me anything about the family! Like, Who is Bullet Raja of the family?",
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
        "chat_welcome": "परिवार के बारे में कुछ भी पूछें! जैसे,परिवार का बुलेट राजा कौन है?",
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

# --- Helper Functions (No Change) ---
def load_family_data(filepath="family_data.md"):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.error("Error: family_data.md not found.")
        st.stop()
        return None

# --- Feature Functions (No Change) ---
def get_next_event_message(family_data, lang_text):
    today = datetime.now()
    next_event = None
    smallest_delta = timedelta(days=367)
    person_blocks = re.findall(r'---Person Start---(.*?)---Person Ends?---', family_data, re.DOTALL | re.IGNORECASE)
    for block in person_blocks:
        name_match = re.search(r'Name:\s*(.*)', block)
        if not name_match: continue
        name = name_match.group(1).strip()
        event_types = [("Born", lang_text["birthday"]), ("Anniversary", lang_text["anniversary"])]
        for tag, event_name in event_types:
            date_match = re.search(fr'{tag}:\s*([A-Za-z]+\s\d+,?\s?\d*)', block)
            if date_match:
                date_str = date_match.group(1).strip()
                event_date, has_year = None, False
                try:
                    event_date, has_year = datetime.strptime(date_str, '%B %d, %Y'), True
                except ValueError:
                    try:
                        event_date, has_year = datetime.strptime(date_str + ", 1904", '%B %d, %Y'), False
                    except ValueError: continue
                next_occurrence = event_date.replace(year=today.year)
                if next_occurrence < today:
                    next_occurrence = next_occurrence.replace(year=today.year + 1)
                delta = next_occurrence - today
                if 0 <= delta.days < smallest_delta.days:
                    smallest_delta = delta
                    year_diff = next_occurrence.year - event_date.year if has_year else None
                    next_event = {"name": name, "year_diff": year_diff, "date": next_occurrence, "delta": delta, "type": event_name}
    if not next_event: return ""
    event_date_str = next_event['date'].strftime('%B %d')
    delta_days = next_event['delta'].days
    if delta_days == 0: day_info = lang_text["today"]
    elif delta_days == 1: day_info = lang_text["tomorrow"]
    else: day_info = lang_text["in_days"].format(days=delta_days)
    event_details = ""
    if next_event['year_diff'] is not None:
        if next_event['type'] == lang_text["birthday"]: event_details = f"({next_event['year_diff']})"
        else: event_details = f"({next_event['year_diff']} {lang_text['years']})"
    return (f"{lang_text['next_event_header']}**{next_event['name']}'s** {next_event['type']} {event_details} {day_info} on **{event_date_str}**.")

def parse_data_for_quiz(family_data):
    facts = []
    person_blocks = re.findall(r'---Person Start---(.*?)---Person Ends?---', family_data, re.DOTALL | re.IGNORECASE)
    for block in person_blocks:
        name_match = re.search(r'Name:\s*(.*)', block)
        if name_match:
            name = name_match.group(1).strip()
            fact_matches = re.findall(r'(Key Facts|Location|Personality Traits):\s*(.*)', block)
            for fact_type, fact_value in fact_matches:
                facts.append({"person": name, "fact_type": fact_type.strip(), "fact_value": fact_value.strip()})
    return facts

def generate_quiz_question(facts, lang_text):
    if len(facts) < 3: return None
    correct_fact = random.choice(facts)
    question_template = "Regarding {person}, what is one of their {fact_type}?"
    if lang_text == UI_TEXT["Hindi 🇮🇳"]:
        question_template = "{person} के बारे में, उनकी एक {fact_type} क्या है?"
    question = question_template.format(person=correct_fact['person'], fact_type=correct_fact['fact_type'].lower())
    correct_answer = correct_fact['fact_value']
    incorrect_options_pool = [f['fact_value'] for f in facts if f['fact_value'] != correct_answer]
    if len(incorrect_options_pool) < 2: return None
    incorrect_answers = random.sample(incorrect_options_pool, 2)
    options = [correct_answer] + incorrect_answers
    random.shuffle(options)
    return {"question": question, "options": options, "correct_answer": correct_answer}

# --- AI Response Function (MODIFIED FOR OPENROUTER) ---

def get_ai_response(client, messages):
    try:
        # The OpenAI library uses the same syntax, so we only change the model name
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="openrouter/sonoma-sky-alpha" # MODIFIED: New model name
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        st.error(f"An error occurred with the API: {e}")
        return None

# --- Streamlit App ---

st.sidebar.title("Settings")
language = st.sidebar.radio("Choose language | भाषा चुनें", ("English 🇬🇧", "Hindi 🇮🇳"))
lang_text = UI_TEXT[language]

st.set_page_config(page_title=lang_text["page_title"], page_icon="👨‍👩‍👧‍👦")
st.title(lang_text["app_title"])

family_data = load_family_data()

# --- Client Initialization (MODIFIED FOR OPENROUTER) ---
try:
    # Use the OPENROUTER_API_KEY environment variable
    openrouter_api_key = os.environ['OPENROUTER_API_KEY']
    client = OpenAI(
      base_url="https://openrouter.ai/api/v1",
      api_key=openrouter_api_key,
    )
except KeyError:
    # Update the error message to ask for the correct key
    st.error("OPENROUTER_API_KEY not found! Please set it in your .env file or Streamlit Secrets.")
    st.stop()

# --- Rest of the App (Logic is the same, just function name changed) ---
next_event_msg = get_next_event_message(family_data, lang_text)
if next_event_msg:
    st.info(next_event_msg)

tab1, tab2 = st.tabs([lang_text["chat_tab"], lang_text["trivia_tab"]])

with tab1:
    st.write(lang_text["chat_welcome"])
    if "messages" not in st.session_state or st.session_state.get("language") != language:
        st.session_state.language = language
        if language == "English 🇬🇧":
            system_prompt = f"""You are a witty, creative, and respectful AI assistant for a family. Your name is 'FamBot'. Your strict rules are: be funny, respectful, diplomatic, and always add a fun fact. Base all your answers strictly on the following Family Knowledge Base.\n---\nFamily Knowledge Base:\n{family_data}\n---"""
        else: # Hindi
            system_prompt = f"""आप परिवार के लिए एक मजाकिया, रचनात्मक और सम्मानजनक एआई सहायक हैं। आपका नाम 'FamBot' है। आपका पूरा वार्तालाप हिंदी में होना चाहिए।\nआपके सख्त नियम हैं:\n1. पहले, दिए गए ज्ञान के आधार पर उपयोगकर्ता के प्रश्न का सीधे उत्तर दें।\n2. उत्तर के बाद, हमेशा एक संबंधित, रचनात्मक "रोचक तथ्य" (fun fact) जोड़ें।\n3. व्यक्तिपरक प्रश्नों के लिए (जैसे "सबसे बुद्धिमान कौन है?"), आपको कूटनीतिक होना चाहिए।\n4. आपका लहजा मजाकिया, आकर्षक और हमेशा सम्मानजनक होना चाहिए।\n5. अपने सभी उत्तर केवल निम्नलिखित पारिवारिक ज्ञान के आधार पर दें।\n---\nपारिवारिक ज्ञान:\n{family_data}\n---"""
        st.session_state.messages = [{"role": "system", "content": system_prompt}]
    for message in st.session_state.messages:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    if prompt := st.chat_input(lang_text["chat_input_placeholder"]):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner(lang_text["thinking"]):
                response = get_ai_response(client, st.session_state.messages) # MODIFIED: Call new function name
                if response:
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

with tab2:
    st.header(lang_text["trivia_header"])
    if 'quiz_facts' not in st.session_state:
        st.session_state.quiz_facts = parse_data_for_quiz(family_data)
    if st.button(lang_text["trivia_button"]):
        st.session_state.quiz_question = generate_quiz_question(st.session_state.quiz_facts, lang_text)
        st.session_state.answered = False
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
