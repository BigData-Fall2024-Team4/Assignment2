import streamlit as st
import requests
from question_selection import question_selection_page
from submit_page import submit_page
from summary_page import summary_page
import os

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://fastapi-app:8000")
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'token' not in st.session_state:
    st.session_state['token'] = None

def register_user(name, email, password):
    try:
        response = requests.post(f"{FASTAPI_URL}/register", json={"email": email, "password": password})
        if response.status_code == 200:
            return True, "Registration successful!"
        else:
            try:
                error_details = response.json().get("detail", "Registration failed!")
                if isinstance(error_details, list):
                    error_messages = []
                    for err in error_details:
                        location = ".".join(err.get('loc', []))
                        message = err.get('msg', '')
                        error_messages.append(f"{location}: {message}")
                    return False, "; ".join(error_messages)
                return False, error_details
            except requests.exceptions.JSONDecodeError:
                return False, "Registration failed due to a server error. Please try again."
    except requests.RequestException as e:
        return False, f"An error occurred: {str(e)}"

def authenticate_user(email, password):
    response = requests.post(f"{FASTAPI_URL}/token", data={"username": email, "password": password})
    if response.status_code == 200:
        token_data = response.json()
        st.session_state['token'] = token_data['access_token']
        return True, "Login successful!"
    else:
        return False, "Incorrect email or password."

def show_login_page():
    st.title("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        success, message = authenticate_user(email, password)
        if success:
            st.success(message)
            st.session_state['logged_in'] = True
            st.session_state['user_email'] = email
            st.rerun()
        else:
            st.error(message)

def show_register_page():
    st.title("Register")
    name = st.text_input("Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    
    if password != confirm_password:
        st.warning("Passwords do not match!")
    
    if st.button("Register"):
        if password == confirm_password:
            success, message = register_user(name, email, password)
            if success:
                st.success(message)
            else:
                st.error(message)

def add_user_history(user_email, question, attempt1, attempt2, level):
    headers = {"Authorization": f"Bearer {st.session_state['token']}"}
    response = requests.post(f"{FASTAPI_URL}/user-history", 
                             json={
                                 "user_email": user_email,
                                 "user_question": question,
                                 "user_attempt_answer_1": attempt1,
                                 "user_attempt_answer_2": attempt2,
                                 "question_level": level
                             },
                             headers=headers)
    if response.status_code != 200:
        st.error("Failed to save user history")

def main():
    if not st.session_state['logged_in']:
        st.sidebar.title("Navigation")
        page = st.sidebar.radio("Go to", ["Login", "Register"])
        
        if page == "Login":
            show_login_page()
        elif page == "Register":
            show_register_page()
    else:
        st.sidebar.title("Navigation")
        nav_option = st.sidebar.radio("Go to", ["Question Selection", "Submit", "Summary"])
        
        if st.sidebar.button("Logout"):
            st.session_state['logged_in'] = False
            st.session_state['current_page'] = 'login'
            st.rerun()
        
        if nav_option == "Question Selection":
            question_selection_page()
        elif nav_option == "Submit":
            submit_page()
        elif nav_option == "Summary":
            summary_page()
    

main()