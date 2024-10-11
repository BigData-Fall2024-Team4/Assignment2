import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://fastapi-app:8000")

def get_edit_steps(file_name):
    try:
        response = requests.get(
            f"{API_URL}/edit_steps",
            params={"file_name": file_name},
            headers={"Authorization": f"Bearer {st.session_state.get('token', '')}"}
        )
        response.raise_for_status()
        return response.json().get("edit_steps", "No edit steps available")
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch edit steps: {str(e)}")
        return "Error fetching edit steps"

def get_processed_file_content(file_name, api):
    """Fetches the processed file content from the appropriate GCP SQL table."""
    try:
        table = "files_pypdf" if api == "pypdf" else "files_azure"
        response = requests.get(
            f"{API_URL}/processed_file",
            params={"file_name": file_name, "table": table},
        )
        response.raise_for_status()
        return response.json().get("processed_content", "No content available")
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch processed file content: {str(e)}")
        return "Error fetching content"

def submit_answer(question, processed_content, api, file_name, edit_steps=None):
    """Submits the answer to the FastAPI backend and gets OpenAI response."""
    try:
        prompt = f"Answer the following question based on the provided content:\n\nQuestion: {question}\nContent: {processed_content}"
        
        # Include edit steps in the prompt if available
        if edit_steps:
            prompt += f"\nEdit Steps: {edit_steps}\nAnswer:"

        response = requests.post(
            f"{API_URL}/submit_answer",
            json={
                "question": question,
                "processed_content": processed_content,
                "api": api,
                "file_name": file_name
            },
        )
        response.raise_for_status()
        return response.json().get("response", "No response available")
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to submit answer: {str(e)}")
        return f"Error submitting answer: {str(e)}"

def call_me():
    if 'show_chat_button' not in st.session_state:
        st.session_state.show_chat_button = False
    st.subheader("Edit Steps:")
    selected_file_name = st.session_state.get('selected_file_name', 'No file selected')
    edit_steps = get_edit_steps(selected_file_name)
    
    if edit_steps != "Error fetching edit steps":
        st.text_area("Edit Steps Content", value=edit_steps, height=500, disabled=True)
        st.session_state.edit_steps_content = edit_steps
        st.session_state.show_chat_button = True
    if st.session_state.show_chat_button:
        if st.button("Get OpenAI Response with Edit Steps"):
            call_cha()
    # else:
    #     st.warning("No edit steps found for this file.")
    #     st.session_state.edit_steps_content = None
        # st.session_state.show_chat_button = False


def call_cha():
    
    # Get the stored processed content from the session state
    processed_content = st.session_state.get('processed_content', '')
    question = st.session_state.get('selected_question', 'No question selected')
    selected_api = st.session_state.get('selected_api', 'No API selected')
    selected_file_name = st.session_state.get('selected_file_name', 'No file selected')
    openai_response = submit_answer(
        question, processed_content, selected_api, selected_file_name, edit_steps=st.session_state.edit_steps_content
    )
    st.subheader("OpenAI Response with Edit Steps:")
    st.write(openai_response)
    # st.session_state.show_chat_button = False  # Hide the chat button after getting a response

def submit_page():
    st.title("Submit Page")

    # Initialize session state variables if they don't exist
    if 'show_edit_steps' not in st.session_state:
        st.session_state.show_edit_steps = False
    if 'edit_steps_content' not in st.session_state:
        st.session_state.edit_steps_content = None

    # Display all selected information
    st.subheader("Selected Information")
    selected_question = st.session_state.get('selected_question', 'No question selected')
    selected_task_id = st.session_state.get('selected_task_id', 'No task selected')
    selected_file_name = st.session_state.get('selected_file_name', 'No file selected')
    selected_api = st.session_state.get('selected_api', 'No API selected')
    selected_final_answer = st.session_state.get('selected_final_answer', 'No answer selected')

    st.write(f"**Selected Question:** {selected_question}")
    st.write(f"**Task ID:** {selected_task_id}")
    st.write(f"**File Name:** {selected_file_name}")
    st.write(f"**Selected API:** {selected_api}")
    st.write(f"**Expected Answers:** {selected_final_answer}")

    st.write("**Processed File Content**")

    # Check if the file is a PDF
    if not selected_file_name or not selected_file_name.lower().endswith('.pdf'):
        processed_content = "The file is not a PDF so there is no processed file for the same."
        st.write(processed_content)
    else:
        with st.spinner("Fetching processed file content..."):
            processed_content = get_processed_file_content(selected_file_name, selected_api)
        st.text_area("", value=processed_content, disabled=True)
        st.session_state.processed_content = processed_content

    if st.button("Submit Answer"):
        with st.spinner("Submitting answer and generating response..."):
            openai_response = submit_answer(selected_question, processed_content, selected_api, selected_file_name)
        if openai_response != "No response available":
            st.subheader("OpenAI Response:")
            st.write(openai_response)

            if selected_final_answer.lower() in openai_response.lower():
                st.success("The answer may be correct.")
            else:
                st.warning("The answer may not be correct.")
                # Enable the "Mark Wrong" button
                st.session_state.show_edit_steps = True

    # Display edit steps if "Mark Wrong" was clicked
    if st.session_state.show_edit_steps:
        if st.button("Mark Wrong"):
            call_me()

if __name__ == "__main__":
    submit_page()
