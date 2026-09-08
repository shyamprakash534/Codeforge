"""Streamlit operator UI for running and inspecting CodeForge workflows."""
import streamlit as st
from codeforge.core.orchestration.orchestrator import CodeForgeOrchestrator
st.set_page_config(page_title='CodeForge',layout='wide')
st.title('CodeForge — Autonomous Software Factory')
st.caption('Plan → Research → Architect → Code → Test → Review → Security → Approval')
repo=st.text_input('Repository path','.')
request=st.text_area('Feature request','Add a health endpoint')
approved=st.checkbox('Approve sensitive changes')
if st.button('Run CodeForge',type='primary'):
    with st.spinner('Running workflow...'):
        state=CodeForgeOrchestrator(repo).run(request,approved=approved)
    st.subheader(f'Status: {state.phase.value}')
    st.json(state.model_dump())
