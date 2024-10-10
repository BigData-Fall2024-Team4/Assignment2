import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://fastapi-app:8000")

def get_processed_file_content(file_name, api):
    """Fetches the processed file content from the appropriate GCP SQL table."""
    try:
        table = "files_pypdf" if api == "pypdf" else "files_azure"
        # headers = {"Authorization": f"Bearer {st.session_state.get('token', '')}"}
        response = requests.get(
            f"{API_URL}/processed_file",
            params={"file_name": file_name, "table": table},
            # headers=headers
        )
        response.raise_for_status()
        return response.json().get("processed_content", "No content available")
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch processed file content: {str(e)}")
        return "Error fetching content"

def submit_answer(question, processed_content, api,file_name):
    """Submits the answer to the FastAPI backend and gets OpenAI response."""
    try:
        # headers = {"Authorization": f"Bearer {st.session_state.get('token', '')}"}
        response = requests.post(
            f"{API_URL}/submit_answer",
            json={
                "question": question,
                "processed_content": processed_content,
                "api": api,
                "file_name" : file_name
            },
            # headers=headers
        )
        response.raise_for_status()
        return response.json().get("response", "No response available")
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to submit answer: {str(e)}")
        return f"Error submitting answer: {str(e)}"

def submit_page():
    st.title("Submit Page")
    
    # Display all selected information
    st.subheader("Selected Information")
    selected_question = st.session_state.get('selected_question', 'No question selected')
    selected_task_id = st.session_state.get('selected_task_id', 'No task selected')
    selected_file_name = st.session_state.get('selected_file_name', 'No file selected')
    selected_api = st.session_state.get('selected_api', 'No API selected')
    
    st.write(f"**Selected Question:** {selected_question}")
    st.write(f"**Task ID:** {selected_task_id}")
    st.write(f"**File Name:** {selected_file_name}")
    st.write(f"**Selected API:** {selected_api}")
    
    st.write("Processed File Content")
    
    # Check if the file is a PDF
    if not selected_file_name or not selected_file_name.lower().endswith('.pdf'):
        processed_content = "The file is not a PDF so there is no processed file for the same."
        st.write(processed_content)
    else:
        with st.spinner("Fetching processed file content..."):
            processed_content = get_processed_file_content(selected_file_name, selected_api)
        st.text_area("Processed File Content:", value=processed_content, height=200, disabled=True)
    
    if st.button("Submit Answer"):
        with st.spinner("Submitting answer and generating response..."):
            openai_response = submit_answer(selected_question, processed_content, selected_api, selected_file_name)
        if openai_response != "No response available":
            st.subheader("OpenAI Response:")
            st.write(openai_response)
        else:
            st.error("Failed to get a response from OpenAI. Please try again.")
    
    if st.button("Back to Question Selection"):
        st.session_state.page = "question_selection"
        st.experimental_rerun()
        
def main():
    submit_page()

if __name__ == "main":
    main()