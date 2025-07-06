import re
import docx
import pdfplumber
from .cv_keywords import *
from unidecode import unidecode


def extract_text_from_pdf(file):
    try:
        with pdfplumber.open(file) as pdf:
            return "\n".join([page.extract_text() or '' for page in pdf.pages])
    except Exception as e:
        print("❌ Error extrayendo texto del PDF:", e)
        return ""


def extract_text_from_docx(file):
    try:
        doc = docx.Document(file)
        return "\n".join([parag.text for parag in doc.paragraphs])
    except Exception as e:
        print("❌ Error extrayendo texto del PDF:", e)
        return ""


def clean_text(text):
    text = unidecode(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text
    
 
def extract_full_name(text):
    if not text:
        return "", ""
    lines = text.strip().split('\n')
    for line in lines[:5]:
        line = line.strip()
        if len(line.split()) >= 2 and '@' not in line.lower() and not any(c in line for c in ":|/\\"):
            return line
    return ""


def split_name(full_name):
    if not full_name:
        print("acá está el error, 2")
        return "", ""
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])
    return full_name


def extract_email(text):
    match = re.search('r[\w\.-]+@[\w\.-]+', text)
    return match.group() if match else None


def extract_phone(text):
    match = re.search(r'(\+\d{1,4})?[\s\-]?\(?\d{2,4}\)?[\s\-]?\d{6,10}', text)
    if match:
        number = match.group()
        code = re.search(r'\+(\d{1,1})', number)
        return code.group() if code else '', number
    return '', ''


def extract_city(text):
    for city in CITY_KEYWORDS:
        if city.lower() in text.lower():
            return city
    return ""


def extract_prof_title(text):
    lines = text.lower().split('\n')
    for line in lines[:10]:
        for kw in TITLE_KEYWORDS:
            if kw.lower() in line:
                return line.strip().capitalize()
    return ""


def extract_summary(text):
    blocks = text.lower().split('\n')
    for i, line in enumerate(blocks):
        if 'perfil profesional' in line or 'sobre mi' in line or 'summary' in line:
            return " ".join(blocks[i+1:i+4])
    return ''


def extract_education(text):
    lines = text.lower().split('\n')
    found_lines = []
    for line in lines:
        if any(kw.lower() in line for kw in EDUCATION_KEYWORDS):
            found_lines.append(line.strip())
    return ". ".join(set(found_lines))


def extract_experience(text):
    lines = text.lower().split()
    found = []
    capture = False
    for line in lines:
        if any(kw.lower() in line for kw in EXPERIENCE_KEYWORDS):
            capture = True
        if capture:
            found.append(line.strip())
            if len(found) >= 6:
                break
    return ". ".join(found)


def extract_skills(text, skill_keywords):
    found = [kw for kw in skill_keywords if kw.lower() in text.lower()]
    return list(set(found))


def extract_linkedin(text):
    match = re.search(r'(https?://)?(www\.)?linkedin\.com/[^\s]+', text)
    return match.group() if match else None


def extract_portfolio(text):
    pattern = r'(https?://[^\s]*\.(dev|me|xyz|github\.io|vercel\.app|netlify\.app|github\.com|behance\.net)[^\s]*)'
    match = re.search(pattern, text)
    return match.group() if match else ""


def analyze_cv(file, filetype='pdf'):
    if filetype == 'pdf':
        text = extract_text_from_pdf(file)
    elif filetype == 'docx':
        text = extract_text_from_docx(file)
    else:
        return {}
    
    text = clean_text(text)
    full_name = extract_full_name(text)
    first_name, last_name = split_name(full_name)
    
    return {
        "first_name": first_name,
        "last_name": last_name,
        "phone_code": extract_phone(text)[0],
        "phone_number": extract_phone(text)[1],
        "city": extract_city(text),
        "professional_title": extract_prof_title(text),
        "summary": extract_summary(text),
        "education": extract_education(text),
        "skills": ", ".join(extract_skills(text, SKILL_KEYWORDS)),
        "experience": extract_experience(text),
        "linkedin_url": extract_linkedin(text),
        "portfolio_url": extract_portfolio(text),
    }