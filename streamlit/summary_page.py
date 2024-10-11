import streamlit as st
import requests
import os,pathlib
from dotenv import load_dotenv
load_dotenv()

env_path = pathlib.Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

API_URL = os.getenv("FASTAPI_URL")

def generate_summary(file_name):
    """Sends the file name to the FastAPI backend to generate a summary."""
    try:
        response = requests.post(
            f"{API_URL}/generate_summary",
            json={"file_name": file_name}
        )
        response.raise_for_status()
        return response.json().get("summary", "No summary available")
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to generate summary: {str(e)}")
        return f"Error generating summary: {str(e)}"

def summary_page():
    st.title("Summary Page")
    
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

    if st.button("Generate Summary"):
        if selected_file_name:
            with st.spinner("Generating summary..."):
                summary = generate_summary(selected_file_name)
            if summary != "No summary available":
                st.subheader("Generated Summary:")
                st.write(summary)
            else:
                st.error("Failed to generate a summary. Please try again.")
        else:
            st.warning("No file name selected. Please select a file from the previous page.")

    

def main():
    summary_page()

if __name__ == "__main__":
    main()