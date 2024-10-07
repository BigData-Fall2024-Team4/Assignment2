import streamlit as st
import requests
from question_selection import question_selection_page
import os

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://fastapi-app:8000")
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def register_user(name, email, password):
    response = requests.post(f"{FASTAPI_URL}/register", json={"name": name, "email": email, "password": password})
    if response.status_code == 200:
        return True, "Registration successful!"
    else:
        return False, response.json().get("detail", "Registration failed!")

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