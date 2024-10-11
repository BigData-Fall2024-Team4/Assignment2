import streamlit as st
import requests
import os
from submit_page import submit_page
from summary_page import summary_page
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://fastapi-app:8000")

def get_data_from_gcp(file_type, dataset):
    """Fetches question data from the FastAPI backend."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.get('token', '')}"}
        response = requests.get(f"{API_URL}/questions", params={"file_type": file_type, "dataset": dataset}, headers=headers)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        return response.json()  # Returns the data as JSON
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to connect to the API: {str(e)}")
        return None

def logout():
    """Handles user logout by clearing session state and token."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state['logged_in'] = False
    st.session_state['token'] = None
    st.rerun()

def question_selection_page():
    st.title("Question Selection")

    # Question Selection page content
    col1, col2 = st.columns(2)

    with col1:
        st.write("Select file type:")
        file_type = st.radio("File type", ("All", "PDF", "Other"), label_visibility="collapsed", key="file_type_radio")
    
    with col2:
        st.write("Select dataset:")
        dataset = st.radio("Dataset", ("Validation", "Test", "Both"), label_visibility="collapsed", key="dataset_radio")
    
    data = get_data_from_gcp(file_type.lower(), dataset.lower())

    if data:
        questions = [""] + [item['question'] for item in data]
        selected_question = st.selectbox("Select a question:", questions, index=0, key="question_select")

        selected_task = None
        if selected_question:
            selected_task = next((item for item in data if item['question'] == selected_question), None)
            if selected_task:
                st.text_input("Associated File:", value=selected_task['file_name'], disabled=True, key="associated_file")

                # Display the final answer, now accessed consistently
                st.text_area("Expected Answer:", value=selected_task['final_answer'], disabled=True, key="final_answer")

        # Show API selection only if the selected file type is "PDF"
        if file_type == "PDF":
            st.write("### Which API should we use to extract pdf data into text?")
            selected_api = st.radio("Select API", ["pypdf", "azure"], horizontal=True, key="api_radio")

            if selected_task:
                st.session_state.selected_question = selected_task['question']
                st.session_state.selected_task_id = selected_task['task_id']
                st.session_state.selected_file_name = selected_task['file_name']
                st.session_state.selected_api = selected_api
                st.session_state.selected_final_answer = selected_task.get('final_answer', 'No final answer available')
        elif file_type == "Other":
            # Store the question without API selection if the file type is "Other"
            if selected_task:
                st.session_state.selected_question = selected_task['question']
                st.session_state.selected_task_id = selected_task['task_id']
                st.session_state.selected_file_name = selected_task['file_name']
                st.session_state.selected_final_answer = selected_task.get('final_answer', 'No final answer available')
            else:
                st.warning("Please select a question before proceeding.")
    else:
        st.error("No data available. Please check your API connection.")

    # Add buttons for Submit and Summary pages
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Submit"):
            submit_page()

    with col2:
        if st.button("Summary"):
            summary_page()

def main():
    question_selection_page()

if __name__ == "main":
    main()

