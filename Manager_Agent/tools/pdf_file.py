from fpdf import FPDF
import os
from PyPDF2 import PdfMerger
import re
from datetime import datetime

def extract_image_filename(text):
    pattern = r"(?:'|\")?(?:\./)?([^'\"\s]+?\.(?:png|jpg|jpeg|bmp|gif))(?:'|\")?"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1) if match else None

class TimestampedPDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        page_num = f"Page {self.page_no()}"
        self.cell(0, 10, page_num, 0, 0, 'C')

    def add_markdown_section(self, text):
        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("### "):
                self.set_font("Arial", "B", 14)
                self.multi_cell(0, 10, line.replace("### ", ""))
            elif line.startswith("#### "):
                self.set_font("Arial", "B", 12)
                self.multi_cell(0, 10, line.replace("#### ", ""))
            elif line.startswith("- "):
                self.set_font("Arial", "", 12)
                # Remove bold markdown if present (**) for simplicity
                line_content = re.sub(r"\*\*(.*?)\*\*", r"\1", line[2:])
                self.multi_cell(0, 10, '* ' + line_content)
            else:
                self.set_font("Arial", "", 12)
                self.multi_cell(0, 10, re.sub(r"\*\*(.*?)\*\*", r"\1", line))


def save_query_result_to_pdf(query: str, image_path: str = None, result_text: str = "", output_pdf: str = "analysis_file.pdf"):
    try:
        temp_pdf = "temp_entry.pdf"
        pdf = TimestampedPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pdf.set_font("Arial", "I", 10)
        pdf.cell(0, 10, f"Generated on: {timestamp}", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.multi_cell(0, 10, "Query:")
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 10, query)
        pdf.ln(5)
        if image_path:
            cleaned_path = extract_image_filename(image_path)
            if cleaned_path and os.path.isfile(cleaned_path):
                try:
                    pdf.set_font("Arial", "B", 12)
                    pdf.multi_cell(0, 10, "Image Used:")
                    pdf.image(cleaned_path, x=10, w=100)
                    pdf.ln(10)
                except RuntimeError as e:
                    pdf.multi_cell(0, 10, f"[Image load error: {str(e)}]")
            else:
                pdf.multi_cell(0, 10, f"[Image not found or invalid path: {image_path}]")

        pdf.set_font("Arial", "B", 12)
        pdf.multi_cell(0, 10, "Result:")
        pdf.set_font("Arial", "", 12)
        pdf.add_markdown_section(result_text)

        pdf.output(temp_pdf)

        merger = PdfMerger()
        if os.path.exists(output_pdf):
            merger.append(output_pdf)
        merger.append(temp_pdf)
        merger.write(output_pdf)
        merger.close()

        os.remove(temp_pdf)
        return output_pdf

    except Exception as e:
        print(f"Error saving PDF: {e}")
        return None
