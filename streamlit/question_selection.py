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

    # Create two columns for the radio buttons
    col1, col2 = st.columns(2)

    # Add radio buttons for file type selection in the first column
    with col1:
        st.write("Select file type:")
        file_type = st.radio("File type", ("All", "PDF", "Other"), label_visibility="collapsed")
    
    # Add radio buttons for dataset selection in the second column
    with col2:
        st.write("Select dataset:")
        dataset = st.radio("Dataset", ("Validation", "Test", "Both"), label_visibility="collapsed")
    
    # Fetch data from the FastAPI backend based on file type and dataset
    data = get_data_from_gcp(file_type.lower(), dataset.lower())

    if data:
       # Create a list of questions
        questions = [""] + [item['question'] for item in data]

        # Dropdown for selecting a question
        selected_question = st.selectbox("Select a question:", questions, index=0)

        # Display file name in a non-editable text box
        if selected_question:
            selected_task = next((item for item in data if item['question'] == selected_question), None)
            if selected_task:
                st.text_input("Associated File:", value=selected_task['file_name'], disabled=True)

        # Add title for API selection
        st.write("### Which API should we use to extract pdf data into text?")

        # Create two columns for the new radio buttons
        api_col1, api_col2 = st.columns(2)

        # Add radio buttons for API selection
        selected_api = st.radio("Select API", ["PyPDF", "Azure"], horizontal=True)

        if st.button("Submit"):
            if selected_question and selected_question != "":
                # Reset openai_response when a new question is selected
                if 'openai_response' in st.session_state:
                    st.session_state.pop('openai_response')

                # Set the selected question and task_id
                task_id = selected_question.split("(ID: ")[-1].strip(")")
                selected_task = next((item for item in data if item['task_id'] == task_id), None)
                if selected_task:
                    st.session_state.selected_question = selected_task['question']
                    st.session_state.selected_task_id = selected_task['task_id']
                    st.session_state.selected_file_name = selected_task['file_name']
                    st.session_state.selected_api = selected_api
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