# print("Hello from the Web Browser Upload!")
# print(2 + 2)



from reportlab.pdfgen import canvas

def create_pdf(filename):
    # Create PDF canvas
    c = canvas.Canvas(filename)

    # Write text
    c.setFont("Helvetica", 16)
    c.drawString(100, 750, "Hello! This PDF is generated using Python.")

    # Add more text
    c.setFont("Helvetica", 12)
    c.drawString(100, 720, "ReportLab makes PDF generation easy.")

    # Save the PDF
    c.save()
    print(f"PDF '{filename}' created successfully.")

# Run the function
create_pdf("output.pdf")
