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
    
 
def extract_full_name(text, city):
    # Normalizer and clean text
    data = text.split('.')[0].strip()
    city_clean = unidecode(city)
    city_index = data.find(city_clean)
    # Obtain only names without city
    name_part = data[:city_index].strip().split()
    if len(name_part) == 2:
        first_name = name_part[0]
        last_name = name_part[1]
    elif len(name_part) == 3:
        first_name = " ".join(name_part[0:2])
        last_name = name_part[2]
    elif len(name_part) == 4:
        first_name = " ".join(name_part[0:2])
        last_name = " ".join(name_part[2:4])
    # If full name have more 5 words
    else:
        first_name = " ".join(name_part[0:2])
        last_name = " ".join(name_part[2:])  
    return first_name, last_name


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
    city_candidates.sort(key=lambda x: x[1])
    best_match = city_candidates[0][0]
    return best_match
    

def extract_prof_title(summary):
    if not summary:
        return ""
    max_score = 0
    best_title = ""
    for title, keywords in TITLE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in summary.lower())
        
        if score > max_score:
            max_score = score
            best_title = title
    if best_title:
        return best_title
    return summary.split('.')[0].strip()  


def extract_summary(text):
    lines = text.strip().split()
    for line in lines:
        if "@" in line:
            start_symmary = len(line) + text.find(line)
        if line.isupper() and line in EXPERIENCE_KEYWORDS:
            end_summary = text.find(line)
            summary = text[start_symmary:end_summary]
    return summary


def extract_education(text):
    clear_text = unidecode(text)
    lines = clear_text.strip().split()
    edu_section_start = ""
    edu_section_end = ""
    for line in lines:
        if line.upper() in START_EDUCATION_SECTION:
            edu_section_start = line
        if line.upper() in END_EDUCATION_SECTION:
            edu_section_end = line
    pattern = rf"{edu_section_start}(.*?){edu_section_end}"
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
    print("🔍 Analizando CV...")
    if filetype == 'pdf':
        text = extract_text_from_pdf(file)
    elif filetype == 'docx':
        text = extract_text_from_docx(file)
    else:
        return {}
    text = clean_text(text)
    phone_code = extract_phone(text)[0]
    phone_number = extract_phone(text)[1]
    city = extract_city(text, extract_phone(text)[0])
    first_name = extract_full_name(text, city)[0]
    last_name = extract_full_name(text, city)[1]
    return {
        "first_name": first_name,
        "last_name": last_name,
        "phone_code": phone_code,
        "phone_number": phone_number,
        "city": city,
        "professional_title": extract_prof_title(text),
        "summary": extract_summary(text),
        "education": extract_education(text),
        "skills": ", ".join(extract_skills(text, SKILLS_KEYWORDS)),
        "experience": extract_experience(text),
        "linkedin_url": extract_linkedin(text),
        "portfolio_url": extract_portfolio(text),
    }