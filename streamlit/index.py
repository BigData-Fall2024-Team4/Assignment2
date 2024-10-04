import streamlit as st
from question_selection import question_selection_page

# Simulated database in session state
if 'users' not in st.session_state:
    st.session_state['users'] = {}

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# Registration function
def register_user(email, password):
    if email in st.session_state['users']:
        return False, "User already exists!"
    else:
        st.session_state['users'][email] = password
        return True, "Registration successful!"

# Authentication function
def authenticate_user(email, password):
    if email in st.session_state['users'] and st.session_state['users'][email] == password:
        return True, "Login successful!"
    else:
        return False, "Incorrect email or password."

# Login page
def show_login_page():
    st.title("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        success, message = authenticate_user(email, password)
        if success:
            st.success(message)
            st.session_state['logged_in'] = True
            st.rerun()  # This will cause the app to rerun and show the question selection page
        else:
            st.error(message)

# Register page
def show_register_page():
    st.title("Register")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    
    if password != confirm_password:
        st.warning("Passwords do not match!")
    
    if st.button("Register"):
        if password == confirm_password:
            success, message = register_user(email, password)
            if success:
                st.success(message)
            else:
                st.error(message)

# Main app logic
def main():
    if st.session_state['logged_in']:
        question_selection_page()
    else:
        st.sidebar.title("Navigation")
        page = st.sidebar.radio("Go to", ["Login", "Register"])
        
        if page == "Login":
            show_login_page()
        elif page == "Register":
            show_register_page()

if __name__ == '__main__':
    main()