import streamlit as st
from gcp_utils import get_data_from_gcp

def question_selection_page():
    st.title("Question Selection")
        # Add a logout button
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()
    
    
    # Add radio buttons for file type selection
    file_type = st.radio("Select file type:", ("PDF", "Other"))
    
    # Add radio buttons for dataset selection
    dataset = st.radio("Select dataset:", ("Validation", "Test", "Both"))
    
    # Fetch data from the GCP database based on file type and dataset
    if file_type == "PDF":
        data = get_data_from_gcp('pdf', dataset.lower())
    else:
        data = get_data_from_gcp('other', dataset.lower())

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
        st.error("No data available. Please check your database connection.")

# Remove the main() function and __main__ check