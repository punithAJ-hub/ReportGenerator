import streamlit as st
import pandas as pd
from pdf_generator import generate_pdf
from excel_parser import read_excel

# Streamlit UI for Home Page
st.title("Project Report Generator")

# File uploader to upload Excel file
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

# Global state to store project details and media
if 'project_details' not in st.session_state:
    st.session_state.project_details = {}

if 'media' not in st.session_state:
    st.session_state.media = {}

# Home Page Logic: After file upload, display form
if uploaded_file is not None:
    df = read_excel(uploaded_file)  # Read Excel data
    st.write(df.head())  # Display first few rows for validation

    # Autofill Project Number field
    project_number = st.selectbox("Project Number", df['Project Number'].unique())
    project_name = df[df['Project Number'] == project_number]['Project Name'].values[0]
    st.text_input("Project Name", project_name, disabled=True)

    # Scope of Work: Multi-select dropdown
    scope_of_work = st.multiselect("Scope of Work", options=["Grade beam", "SOG", "Steel Framing"])

    # Prepared By: Dropdown with fake employee names
    employee_names = ["John Doe", "Jane Smith", "Emily Davis"]
    prepared_by = st.selectbox("Prepared By", employee_names)

    # Other fields
    project_address = st.text_input("Project Address")
    client_name = st.text_input("Client Name")
    date_of_visit = st.date_input("Date of Visit")
    weather = st.text_input("Weather")
    date_of_report = st.date_input("Date of Report")
    present = st.text_input("Present (eg, Engineer Name, Company Name)")
    remarks = st.text_area("Remarks")

    # Collecting Observations
    observations = []
    observation_count = st.number_input("Number of Observations", min_value=1, max_value=10)
    for i in range(observation_count):
        observation = st.text_input(f"Observation {i + 1}")
        observations.append(observation)

    # Passing all form data to PDF generation
    if st.button("Next"):
        st.session_state.project_details = {
            "project_number": project_number,
            "project_name": project_name,
            "project_address": project_address,
            "client_name": client_name,
            "date_of_visit": date_of_visit.strftime("%d/%m/%Y"),
            "weather": weather,
            "date_of_report": date_of_report.strftime("%d/%m/%Y"),
            "present": present,
            "prepared_by": prepared_by,
            "observations": observations,
            "scope_of_work": scope_of_work,
            "remarks": remarks,
        }
        st.write("Proceed to Media Page")

# Media Page Logic: Upload images and descriptions
if 'media' in st.session_state:
    st.title("Media Page: Upload Images and Descriptions")

    # Upload Image(s)
    uploaded_images = st.file_uploader("Upload Image(s)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

    # Input for Description
    descriptions = []
    for i, img in enumerate(uploaded_images):
        description = st.text_area(f"Enter Description for Image {i + 1}", key=f"description_{i}")
        descriptions.append(description)

    # Store images and descriptions for later use
    if st.button("Submit Media"):
        st.session_state.media = {
            "images": uploaded_images,
            "descriptions": descriptions
        }
        st.write("Media Submitted Successfully")

# PDF Generation Logic
if st.button("Generate PDF Report"):
    pdf_buffer = generate_pdf({
        "project_number": st.session_state.project_details['project_number'],
        "project_name": st.session_state.project_details['project_name'],
        "project_address": st.session_state.project_details['project_address'],
        "client_name": st.session_state.project_details['client_name'],
        "date_of_visit": st.session_state.project_details['date_of_visit'],
        "weather": st.session_state.project_details['weather'],
        "date_of_report": st.session_state.project_details['date_of_report'],
        "present": st.session_state.project_details['present'],
        "prepared_by": st.session_state.project_details['prepared_by'],
        "observations": st.session_state.project_details['observations'],
        "scope_of_work": st.session_state.project_details['scope_of_work'],
        "remarks": st.session_state.project_details['remarks'],
        "media": st.session_state.media
    })
    st.download_button("Download PDF", pdf_buffer, file_name="report.pdf")
