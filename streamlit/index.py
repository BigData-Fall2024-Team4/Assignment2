import streamlit as st
import requests
from question_selection import question_selection_page
import os

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://fastapi-app:8000")
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def register_user(name, email, password):
    try:
        response = requests.post(f"{FASTAPI_URL}/register", json={"name": name, "email": email, "password": password})
        if response.status_code == 200:
            return True, "Registration successful!"
        else:
            # Handle specific validation errors (e.g., minimum password length)
            try:
                error_details = response.json().get("detail", "Registration failed!")
                if isinstance(error_details, list):
                    error_messages = []
                    for err in error_details:
                        # Example: Displaying 'password' validation error: 'Password must be at least 8 characters long'
                        location = ".".join(err.get('loc', []))  # Shows the field where the error occurred (e.g., 'password')
                        message = err.get('msg', '')  # The actual error message
                        error_messages.append(f"{location}: {message}")
                    return False, "; ".join(error_messages)
                return False, error_details
            except requests.exceptions.JSONDecodeError:
                return False, "Registration failed due to a server error. Please try again."
    except requests.RequestException as e:
        return False, f"An error occurred: {str(e)}"

def authenticate_user(email, password):
    response = requests.post(f"{FASTAPI_URL}/login", json={"email": email, "password": password})
    if response.status_code == 200:
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
    response = requests.post(f"{FASTAPI_URL}/user-history", json={
        "user_email": user_email,
        "user_question": question,
        "user_attempt_answer_1": attempt1,
        "user_attempt_answer_2": attempt2,
        "question_level": level
    })
    if response.status_code != 200:
        st.error("Failed to save user history")

def main():
    if st.session_state['logged_in']:
        question_selection_page()
        # After question_selection_page, you might want to add:
        # add_user_history(st.session_state['user_email'], question, attempt1, attempt2, level)
    else:
        st.sidebar.title("Navigation")
        page = st.sidebar.radio("Go to", ["Login", "Register"])
        
        if page == "Login":
            show_login_page()
        elif page == "Register":
            show_register_page()

if __name__ == '__main__':
    main()