import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://fastapi-app:8000")

def get_data_from_gcp(file_type, dataset):
    """Fetches question data from the FastAPI backend."""
    try:
        response = requests.get(f"{API_URL}/questions", params={"file_type": file_type, "dataset": dataset})
        response.raise_for_status()  # Raises an HTTPError for bad responses
        return response.json()  # Returns the data as JSON
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to connect to the API: {str(e)}")
        return None

def question_selection_page():
    st.title("Question Selection")

    # Add a logout button
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()

    # Add radio buttons for file type selection
    file_type = st.radio("Select file type:", ("All", "PDF", "Other"))
    
    # Add radio buttons for dataset selection
    dataset = st.radio("Select dataset:", ("Validation", "Test", "Both"))
    
    # Fetch data from the FastAPI backend based on file type and dataset
    data = get_data_from_gcp(file_type.lower(), dataset.lower())

    if data:
        # Create a list of questions
        questions = [""] + [f"{item['question']} ({item['file_name']})" for item in data]

        # Dropdown for selecting a question
        selected_question = st.selectbox("Select a question:", questions, index=0)

        if st.button("Submit"):
            if selected_question:
                # Reset openai_response when a new question is selected
                if 'openai_response' in st.session_state:
                    st.session_state.pop('openai_response')

                # Set the selected question and task_id
                selected_task = next((item for item in data if f"{item['question']} ({item['file_name']})" == selected_question), None)
                if selected_task:
                    st.session_state.selected_question = selected_task['question']
                    st.session_state.selected_task_id = selected_task['task_id']
                    st.session_state.selected_file_name = selected_task['file_name']
                    st.session_state.current_page = "Answer Comparison"
                    st.rerun()
                else:
                    st.warning("Error retrieving task information.")
            else:
                st.warning("Please select a question before submitting.")
    else:
        st.error("No data available. Please check your API connection.")

if __name__ == "__main__":
    question_selection_page()