import streamlit as st
import os
import re
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Helper Functions ---

def load_family_data(filepath="family_data.md"):
    """Reads the family data from the specified file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.error("Error: family_data.md not found.")
        st.stop()
        return None

# --- "Next Upcoming Event" Feature (MODIFIED) ---

def get_next_event_message(family_data):
    """Finds the single closest upcoming birthday or anniversary."""
    today = datetime.now()
    next_event = None
    smallest_delta = timedelta(days=367)

    person_blocks = re.findall(r'---Person Start---(.*?)---Person Ends---', family_data, re.DOTALL)
    
    for block in person_blocks:
        name_match = re.search(r'Name:\s*(.*)', block)
        if not name_match:
            continue
        
        name = name_match.group(1).strip()
        
        # ## MODIFIED SECTION: Now checks for both Born and Anniversary tags ##
        event_types = [("Born", "birthday"), ("Anniversary", "anniversary")]
        
        for tag, event_name in event_types:
            date_match = re.search(fr'{tag}:\s*(.*)', block)
            if date_match:
                date_str = date_match.group(1).strip()
                try:
                    event_date = datetime.strptime(date_str, '%B %d, %Y')
                    
                    # Calculate the next occurrence
                    next_occurrence = event_date.replace(year=today.year)
                    if next_occurrence < today:
                        next_occurrence = next_occurrence.replace(year=today.year + 1)
                    
                    # Check if this is the closest event so far
                    delta = next_occurrence - today
                    if 0 <= delta.days < smallest_delta.days:
                        smallest_delta = delta
                        year_diff = next_occurrence.year - event_date.year
                        next_event = {
                            "name": name, 
                            "year_diff": year_diff, 
                            "date": next_occurrence, 
                            "delta": delta,
                            "type": event_name
                        }
                except ValueError:
                    continue # Ignore malformed dates
        # ## END OF MODIFIED SECTION ##

    if not next_event:
        return ""

    # Format the final message
    event_date_str = next_event['date'].strftime('%B %d')
    delta_days = next_event['delta'].days
    
    if delta_days == 0:
        day_info = "is today!"
    elif delta_days == 1:
        day_info = "is tomorrow!"
    else:
        day_info = f"is in {delta_days} days"
    
    event_details = f"({next_event['year_diff']})" if next_event['type'] == 'birthday' else f"({next_event['year_diff']} years)"

    message = (f"🗓️ Next Event: **{next_event['name']}'s** {next_event['type']} {event_details} "
               f"{day_info} on **{event_date_str}**.")
    return message

# --- Family Trivia Game Feature ---

def parse_data_for_quiz(family_data):
    """Parses the data file to extract facts for the quiz."""
    facts = []
    person_blocks = re.findall(r'---Person Start---(.*?)---Person Ends---', family_data, re.DOTALL)
    for block in person_blocks:
        name_match = re.search(r'Name:\s*(.*)', block)
        if name_match:
            name = name_match.group(1).strip()
            fact_matches = re.findall(r'(Key Facts|Location|Personality Traits):\s*(.*)', block)
            for fact_type, fact_value in fact_matches:
                facts.append({"person": name, "fact_type": fact_type.strip(), "fact_value": fact_value.strip()})
    return facts

def generate_quiz_question(facts):
    """Generates a single quiz question with multiple choice options."""
    if len(facts) < 3: return None
    correct_fact = random.choice(facts)
    question = f"Regarding {correct_fact['person']}, what is one of their {correct_fact['fact_type'].lower()}?"
    correct_answer = correct_fact['fact_value']
    incorrect_options_pool = [f['fact_value'] for f in facts if f['fact_value'] != correct_answer]
    if len(incorrect_options_pool) < 2: return None
    incorrect_answers = random.sample(incorrect_options_pool, 2)
    options = [correct_answer] + incorrect_answers
    random.shuffle(options)
    return {"question": question, "options": options, "correct_answer": correct_answer}

# --- Chatbot Feature ---

def get_groq_response(client, messages):
    """Gets a response from the Groq API."""
    try:
        chat_completion = client.chat.com.pletions.create(
            messages=messages, model="llama-3.3-70b-versatile")
        return chat_completion.choices[0].message.content
    except Exception as e:
        st.error(f"An error occurred with the API: {e}")
        return None

# --- Streamlit App ---

st.set_page_config(page_title="Family AI", page_icon="👨‍👩‍👧‍👦")
st.title("🤖 The Family AI")

# Load data and initialize Groq client
family_data = load_family_data()
try:
    groq_api_key = os.environ['GROQ_API_KEY']
    client = Groq(api_key=groq_api_key)
except KeyError:
    st.error("GROQ_API_KEY not found! Please set it in your .env file.")
    st.stop()

# Display "Next Event" message
next_event_msg = get_next_event_message(family_data)
if next_event_msg:
    st.info(next_event_msg)

# --- UI Tabs ---
tab1, tab2 = st.tabs(["💬 Chatbot", "🏆 Family Trivia Game"])

# Chatbot Tab
with tab1:
    st.write("Ask me anything about the family!")
    if "messages" not in st.session_state:
        system_prompt = f"""You are a witty, creative, and respectful AI assistant for a family.
        Your strict rules are: be funny, respectful, diplomatic, and always add a fun fact.
        Base all your answers strictly on the following Family Knowledge Base.
        ---
        Family Knowledge Base:
        {family_data}
        ---
        """
        st.session_state.messages = [{"role": "system", "content": system_prompt}]

    for message in st.session_state.messages:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt := st.chat_input("What do you want to know?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = get_groq_response(client, st.session_state.messages)
                if response:
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

# Trivia Game Tab
with tab2:
    st.header("How well do you know the family?")
    if 'quiz_facts' not in st.session_state:
        st.session_state.quiz_facts = parse_data_for_quiz(family_data)
    
    if st.button("Start New Game / Next Question"):
        st.session_state.quiz_question = generate_quiz_question(st.session_state.quiz_facts)
        st.session_state.answered = False

    if 'quiz_question' in st.session_state and st.session_state.quiz_question:
        q = st.session_state.quiz_question
        st.subheader(q['question'])
        with st.form("quiz_form"):
            selected_option = st.radio("Choose your answer:", q['options'], key="quiz_options")
            submitted = st.form_submit_button("Submit Answer")
            if submitted and not st.session_state.get('answered', False):
                st.session_state.answered = True 
                if selected_option == q['correct_answer']:
                    st.success("Correct! You're a family expert!")
                else:
                    st.error(f"Not quite! The correct answer was: {q['correct_answer']}")


