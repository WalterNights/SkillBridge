import re
import docx
import pdfplumber
from .cv_keywords import *
from .cv_countries import *
from unidecode import unidecode
from py_countries_states_cities_database import get_all_countries_and_cities_nested



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
    lines = text.strip().split('\n')
    
    for line in lines[:8]:
        clean = line.strip()
        words = clean.split()
        if len(words) == 2 and all(w[0].isupper() for w in words if w and w[0].isalpha()):
            return clean
    return ""


def split_name(full_name):
    if not full_name:
        return "", ""
    parts = full_name.strip().split()
    return parts[0], " ".join(parts[1:]) if len(parts) > 1 else ""


def extract_section(text, start_keyword, stop_keyword):
    pattern = rf"({'|'.join(start_keyword)})(.*?)(?={'|'.join(stop_keyword)})"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return clean_text(match.group(2)) if match else ""


def extract_phone(text):
    match = re.search(r'(\+\d{1,4})[\s\-]?\(?(\d{2,4})\)?[\s\-]?(\d{6,10})', text)
    if match:
        code = match.group(1)
        number = f"{match.group(2)}{match.group(3)}"
        return code, number
    return '', ''


def extract_city(text, country_name):
    country_found = PHONE_CODE_COUNTRY.get(country_name)
    countrys = get_all_countries_and_cities_nested()
    data = text.split('.')[0]
    city_candidates = []           
    for country in countrys:
        if country['name'] == country_found:
            for city in country['cities']:
                city_find = unidecode(city['name'])
                pos = data.find(city_find)
                if pos != -1:
                    city_candidates.append((city['name'], pos))
                    print(city_candidates)
    city_candidates.sort(key=lambda x: x[1])
    best_match = city_candidates[0][0]
    return best_match
    
    


def extract_prof_title(summary):
    for kw in TITLE_KEYWORDS:
        if kw.lower() in summary.lower():
            return kw
    if summary:
        return summary.split('.')[0].strip()
    return ""


def extract_summary(text):
    lines = text.strip().split('\n')
    summary_lines = []
    capture = False
    for line in lines[:20]:
        clean = line.strip()
        if not clean:
            continue
        if any(x in clean.lower() for x in ["experiencia", "experience"]):
            break
        if len(clean.split()) >= 6:
            summary_lines.append(clean)
            capture = True
        elif capture:
            break
    return clean_text(" ".join(summary_lines))


def extract_education(text):
    pattern = r"EDUCACI[oÓ]N(.*?)SKILLS"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return clean_text(match.group(1))
    return ""


def extract_experience(text):
    pattern = r"EXPERIENCIA PROFESIONAL(.*?)EDUCACI[oÓ]N"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return clean_text(match.group(1))
    return ""


def extract_skills(text, SKILLS_KEYWORDS):
    found = [kw for kw in SKILLS_KEYWORDS if kw.lower() in text.lower()]
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
    
    # Extract Header to Section
    summary = extract_section(text, PROFESSIONAL_RESUME_KEYWORDS, STOP_KEYWORDS["summary"])
    
    return {
        "first_name": first_name,
        "last_name": last_name,
        "phone_code": extract_phone(text)[0],
        "phone_number": extract_phone(text)[1],
        "city": extract_city(text, extract_phone(text)[0]),
        "professional_title": extract_prof_title(text),
        "summary": extract_summary(text),
        "education": extract_education(text),
        "skills": ", ".join(extract_skills(text, SKILLS_KEYWORDS)),
        "experience": extract_experience(text),
        "linkedin_url": extract_linkedin(text),
        "portfolio_url": extract_portfolio(text),
    }