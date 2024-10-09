# pages/2_Summary.py
import streamlit as st

def summary_page():
    st.title("Summary Page")
    
    # Display all selected information
    st.subheader("Selected Information")
    st.write(f"**Selected Question:** {st.session_state.get('selected_question', 'No question selected')}")
    st.write(f"**Task ID:** {st.session_state.get('selected_task_id', 'No task selected')}")
    st.write(f"**File Name:** {st.session_state.get('selected_file_name', 'No file selected')}")
    st.write(f"**Selected API:** {st.session_state.get('selected_api', 'No API selected')}")
    
    # Add a separator
    st.markdown("---")
    
    # Add your summary page specific code here
    st.subheader("Summary Information")
    
    # This is a placeholder. In a real application, you might fetch this data from your backend
    st.write("Total questions answered: 42")
    st.write("Average score: 85%")
    
    # You could add a chart here
    import pandas as pd
    import plotly.express as px
    
    # Sample data
    data = pd.DataFrame({
        'Category': ['Correct', 'Incorrect', 'Partially Correct'],
        'Count': [30, 5, 7]
    })
    
    fig = px.pie(data, values='Count', names='Category', title='Answer Distribution')
    st.plotly_chart(fig)
