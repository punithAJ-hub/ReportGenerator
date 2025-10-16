from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import tempfile
import os


def generate_pdf(data):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    # Title and Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(100, 750, "Field Report")

    c.setFont("Helvetica", 12)
    c.drawString(100, 730, f"Project Number: {data['project_number']}")
    c.drawString(100, 710, f"Project Name: {data['project_name']}")
    c.drawString(100, 690, f"Project Address: {data.get('project_address', 'N/A')}")
    c.drawString(100, 670, f"Client: {data.get('client_name', 'N/A')}")
    c.drawString(100, 650, f"Date of Visit: {data['date_of_visit']}")
    c.drawString(100, 630, f"Weather: {data['weather']}")
    c.drawString(100, 610, f"Date of Report: {data['date_of_report']}")
    c.drawString(100, 590, f"Present: {data['present']}")
    c.drawString(100, 570, f"Prepared By: {data['prepared_by']}")

    # Observations Section
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, 550, "Observations:")

    c.setFont("Helvetica", 12)
    observations = data.get('observations', [])
    y_position = 530
    for observation in observations:
        c.drawString(100, y_position, f"- {observation}")
        y_position -= 20

    # Scope of Work
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, y_position - 20, "Scope of Work:")
    c.setFont("Helvetica", 12)
    scope_of_work = ', '.join(data['scope_of_work'])
    c.drawString(100, y_position - 40, scope_of_work)

    # Remarks Section
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, y_position - 60, "Remarks:")
    c.setFont("Helvetica", 12)
    c.drawString(100, y_position - 80, data.get('remarks', 'N/A'))

    # Media Section (Images and Descriptions)
    y_position -= 100
    if 'images' in data['media']:
        for i, img in enumerate(data['media']['images']):
            # Save the image to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                temp_file.write(img.getvalue())  # Write the image content to the temp file
                temp_file_path = temp_file.name

            # Use the temp file path in drawImage
            c.drawImage(temp_file_path, 100, y_position, width=200, height=150)
            c.drawString(100, y_position - 20, data['media']['descriptions'][i])
            y_position -= 170

            # Optional: Delete the temporary image file after using it
            os.remove(temp_file_path)

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer
