import streamlit as st
from gcp_utils import get_data_from_gcp

def question_selection_page():
    st.title("Question Selection")
    
    # Fetch data from the GCP database
    data = get_data_from_gcp()

    if data:
        # Create a list of questions
        questions = [""] + [item['question'] for item in data]

        # Dropdown for selecting a question
        selected_question = st.selectbox("Select a question:", questions, index=0)

        if st.button("Submit"):
            if selected_question:
                # Reset openai_response when a new question is selected
                if 'openai_response' in st.session_state:
                    st.session_state.pop('openai_response')

                # Set the selected question and task_id
                selected_task = next((item for item in data if item['question'] == selected_question), None)
                if selected_task:
                    st.session_state.selected_question = selected_question
                    st.session_state.selected_task_id = selected_task['task_id']
                    st.session_state.current_page = "Answer Comparison"
                    st.rerun()
                else:
                    st.warning("Error retrieving task information.")
            else:
                st.warning("Please select a question before submitting.")
    else:
        st.error("No data available. Please check your database connection.")

# Remove the main() function and __main__ check