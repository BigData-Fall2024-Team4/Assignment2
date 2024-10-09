# pages/1_Submit.py
import streamlit as st

def submit_page():
    st.title("Submit Page")
    
    # Display all selected information
    st.subheader("Selected Information")
    st.write(f"**Selected Question:** {st.session_state.get('selected_question', 'No question selected')}")
    st.write(f"**Task ID:** {st.session_state.get('selected_task_id', 'No task selected')}")
    st.write(f"**File Name:** {st.session_state.get('selected_file_name', 'No file selected')}")
    st.write(f"**Selected API:** {st.session_state.get('selected_api', 'No API selected')}")
    
    # Add a separator
    st.markdown("---")
    
    # Add your submit page specific code here
    st.subheader("Submit Your Answer")
    user_answer = st.text_area("Enter your answer here:", height=200)
    
    if st.button("Submit Answer"):
        if user_answer:
            # Here you would typically send the answer to your backend
            st.success("Answer submitted successfully!")
        else:
            st.warning("Please enter an answer before submitting.")