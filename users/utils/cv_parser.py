import fitz
import docx


def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text


def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs])


def extrac_text_from_resume(file):
    filename = file.name.lower()
    if filename.endswith(".pdf"):
        return extract_text_from_pdf
    elif filename.endswith(".docx"):
        return extract_text_from_docx
    else:
        return ""