import streamlit as st
import tempfile
import os
import fitz 
import docx
from pptx import Presentation
import comtypes.client
import pythoncom
import requests
import re
os.environ["GOOGLE_API_KEY"] = "AIzaSyAWjOyvXsq6oq_uhduhvP1i4sbYEmBgN1I"
os.environ["GOOGLE_CSE_ID"] = "AIzaSyAWjOyvXsq6oq_uhduhvP1i4sbYEmBgN1I"
google_api_key = os.getenv("GOOGLE_API_KEY")
google_cse_id = os.getenv("GOOGLE_CSE_ID")

if not google_api_key or not google_cse_id:
    raise ValueError("GOOGLE_API_KEY or GOOGLE_CSE_ID not found in environment variables.")

def configure_genai(api_key):
    print("GenAI configured with API key:", api_key)

configure_genai(google_api_key)

def perform_web_search(query):
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "cx": google_cse_id,
        "key": google_api_key,
        "num": 3,
    }
    response = requests.get(search_url, params=params)
    results = response.json()
    search_results = ""
    for item in results.get("items", []):
        search_results += item["snippet"] + "\n"
    return search_results

def extract_text_from_pdf(file):
    text = ""
    pdf_document = fitz.open(stream=file.read(), filetype="pdf")
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        text += page.get_text()
    return text

def extract_text_from_docx(file):
    doc = docx.Document(file)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

def extract_text_from_doc(file):
    text = ""
    try:
        pythoncom.CoInitialize()
        word = comtypes.client.CreateObject('Word.Application')
        with tempfile.NamedTemporaryFile(delete=False, suffix=".doc") as temp_file:
            temp_file.write(file.read())
            temp_file_path = temp_file.name
        doc = word.Documents.Open(temp_file_path, ReadOnly=True)
        text = doc.Content.Text
        doc.Close(False)
        word.Quit()
        os.remove(temp_file_path)
    finally:
        pythoncom.CoUninitialize()
    return text

def extract_text_from_pptx(file):
    text = ""
    try:
        presentation = Presentation(file)
        for slide in presentation.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"
    except Exception as e:
        text = f"Failed to extract text from PPTX: {e}"
    return text

def extract_text_from_ppt(file):
    text = ""
    try:
        pythoncom.CoInitialize()
        ppt = comtypes.client.CreateObject('PowerPoint.Application')
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ppt") as temp_file:
            temp_file.write(file.read())
            temp_file_path = temp_file.name
        presentation = ppt.Presentations.Open(temp_file_path, ReadOnly=True)
        for slide in presentation.Slides:
            for shape in slide.shapes:
                if shape.HasTextFrame and shape.TextFrame.HasText:
                    text += shape.TextFrame.TextRange.Text + "\n"
        presentation.Close()
        ppt.Quit()
        os.remove(temp_file_path)
    finally:
        pythoncom.CoUninitialize()
    return text

def extract_text_from_txt(file):
    text = file.read().decode("utf-8")
    return text

file_type_handlers = {
    "pdf": extract_text_from_pdf,
    "docx": extract_text_from_docx,
    "pptx": extract_text_from_pptx,
    "doc": extract_text_from_doc,
    "ppt": extract_text_from_ppt,
    "txt": extract_text_from_txt,
}

def extract_text(file, file_type):
    handler = file_type_handlers.get(file_type)
    if handler:
        return handler(file)
    else:
        return "Unsupported file type. Please try a PDF, DOCX, PPTX, DOC, PPT, or TXT file."

st.set_page_config(page_title="Study Helper")
st.header("Study Helper")
uploaded_file = st.file_uploader("Upload your document", type=list(file_type_handlers.keys()))

if uploaded_file:
    file_type = uploaded_file.name.split('.')[-1].lower()
    text = extract_text(uploaded_file, file_type)
    
    if "Failed" not in text:
        st.subheader("Document Content")
        st.write(text)  

        if st.button("Generate Quiz"):
            quiz_questions = ["What is the main topic of the document?", "What are the key details mentioned?"]
            quiz_answers = [text.split()[0], text.split()[1]]  
            st.session_state.quiz_questions = quiz_questions
            st.session_state.quiz_answers = quiz_answers
            st.session_state.user_answers = [""] * len(quiz_questions)

        if "quiz_questions" in st.session_state:
            st.subheader("Quiz")
            for i, question in enumerate(st.session_state.quiz_questions):
                st.session_state.user_answers[i] = st.text_input(f"Question {i+1}: {question}", key=f"answer_{i}")

            if st.button("Submit Quiz"):
                correct_answers = 0
                for user_answer, correct_answer in zip(st.session_state.user_answers, st.session_state.quiz_answers):
                    if user_answer.lower().strip() in correct_answer.lower():
                        correct_answers += 1
                total_questions = len(st.session_state.quiz_questions)
                st.success(f"You answered {correct_answers} out of {total_questions} questions correctly.")
    else:
        st.error("Failed to extract text from the document.")
