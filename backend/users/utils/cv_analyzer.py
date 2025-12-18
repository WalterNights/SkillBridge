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
    if not city:
        return "", ""
    city_clean = unidecode(city)
    city_index = data.find(city_clean)
    if city_index == -1:
        return "", ""
    # Obtain only names without city
    name_part = data[:city_index].strip().split()
    if len(name_part) == 0:
        return "", ""
    elif len(name_part) == 1:
        return name_part[0], ""
    elif len(name_part) == 2:
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
    if not country_found:
        return ""
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
    if not city_candidates:
        return ""
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
    start_symmary = 0
    end_summary = len(text)
    for line in lines:
        if "@" in line:
            start_symmary = len(line) + text.find(line)
        if line.isupper() and line in EXPERIENCE_KEYWORDS:
            end_summary = text.find(line)
            break
    summary = text[start_symmary:end_summary].strip()
    return summary


def extract_education(text):
    """
    Extrae la educación del CV en formato estructurado.
    Retorna una lista de diccionarios con: institution, title, start_date, end_date, location_city, location_country
    """
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
    if not match:
        return []

    edu_text = match.group(1).strip()
    educations = []

    # Patrones para detectar fechas
    date_pattern = r'(\b(?:Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*\d{4}|\d{1,2}/\d{4}|\d{4})\s*[-–—a,]\s*(\b(?:Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*\d{4}|\d{1,2}/\d{4}|\d{4}|[Aa]ctual|[Pp]resente|[Pp]resent)'

    # Patrón para detectar ubicaciones (Ciudad, País)
    location_pattern = r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)\s*,\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)'

    # Dividir por fechas encontradas
    date_matches = list(re.finditer(date_pattern, edu_text))

    if not date_matches:
        # Si no hay fechas, retornar como texto
        return clean_text(edu_text)

    for i, date_match in enumerate(date_matches):
        # Obtener el texto antes de esta fecha
        if i == 0:
            before_text = edu_text[:date_match.start()].strip()
        else:
            before_text = edu_text[date_matches[i-1].end():date_match.start()].strip()

        # Extraer fechas
        start_date = date_match.group(1).strip()
        end_date = date_match.group(2).strip()

        # Buscar ubicación en el texto antes de la fecha
        location_match = re.search(location_pattern, before_text)
        location_city = ""
        location_country = ""
        if location_match:
            location_city = location_match.group(1)
            location_country = location_match.group(2)
            # Remover la ubicación del texto
            before_text = before_text[:location_match.start()].strip()

        # El texto restante contiene institución y título
        lines = [l.strip() for l in before_text.split('\n') if l.strip()]
        if not lines:
            lines = [l.strip() for l in before_text.split('.') if l.strip()]

        institution = ""
        title = ""
        if len(lines) >= 2:
            institution = lines[0]
            title = lines[1]
        elif len(lines) == 1:
            # Intentar separar por guión
            parts = re.split(r'\s*[-–—]\s*', lines[0])
            if len(parts) >= 2:
                title = parts[0]
                institution = parts[1]
            else:
                institution = lines[0]

        if institution or title:
            educations.append({
                "institution": institution,
                "title": title,
                "start_date": start_date,
                "end_date": end_date,
                "location_city": location_city,
                "location_country": location_country
            })

    return educations if educations else clean_text(edu_text)


def extract_experience(text):
    """
    Extrae la experiencia laboral del CV en formato estructurado.
    Retorna una lista de diccionarios con: company, position, start_date, end_date, location_city, location_country, description
    """
    pattern = r"EXPERIENCIA PROFESIONAL(.*?)EDUCACI[oÓ]N"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if not match:
        return []

    exp_text = match.group(1).strip()
    experiences = []

    # Patrones para detectar fechas
    date_pattern = r'(\b(?:Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*\d{4}|\d{1,2}/\d{4}|\d{4})\s*[-–—a]\s*(\b(?:Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*\d{4}|\d{1,2}/\d{4}|\d{4}|[Aa]ctual|[Pp]resente|[Pp]resent)'

    # Patrón para detectar ubicaciones (Ciudad, País)
    location_pattern = r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)\s*,\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)'

    # Dividir por fechas encontradas
    date_matches = list(re.finditer(date_pattern, exp_text))

    if not date_matches:
        # Si no hay fechas, retornar como texto
        return exp_text

    for i, date_match in enumerate(date_matches):
        # Obtener el texto antes de esta fecha hasta la fecha anterior
        if i == 0:
            before_text = exp_text[:date_match.start()].strip()
        else:
            before_text = exp_text[date_matches[i-1].end():date_match.start()].strip()

        # Obtener texto después de la fecha (descripción)
        if i < len(date_matches) - 1:
            after_text = exp_text[date_match.end():date_matches[i+1].start()].strip()
        else:
            after_text = exp_text[date_match.end():].strip()

        # Extraer fechas
        start_date = date_match.group(1).strip()
        end_date = date_match.group(2).strip()

        # Buscar ubicación en el texto antes de la fecha
        location_match = re.search(location_pattern, before_text)
        location_city = ""
        location_country = ""
        if location_match:
            location_city = location_match.group(1)
            location_country = location_match.group(2)
            # Remover la ubicación del texto
            before_text = before_text[:location_match.start()].strip()

        # El texto restante contiene empresa y puesto
        lines = [l.strip() for l in before_text.split('\n') if l.strip()]
        if not lines:
            lines = [l.strip() for l in before_text.split('.') if l.strip()]

        company = ""
        position = ""
        if len(lines) >= 2:
            company = lines[0]
            position = lines[1]
        elif len(lines) == 1:
            # Intentar separar por guión o coma
            parts = re.split(r'\s*[-–—]\s*|\s*,\s*', lines[0])
            if len(parts) >= 2:
                company = parts[0]
                position = parts[1]
            else:
                company = lines[0]

        # Limpiar descripción
        description = clean_text(after_text) if after_text else ""

        if company or position:
            experiences.append({
                "company": company,
                "position": position,
                "start_date": start_date,
                "end_date": end_date,
                "location_city": location_city,
                "location_country": location_country,
                "description": description
            })

    return experiences if experiences else exp_text


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
    try:
        if filetype == 'pdf':
            text = extract_text_from_pdf(file)
        elif filetype == 'docx':
            text = extract_text_from_docx(file)
        else:
            print("❌ Formato de archivo no soportado")
            return {}
        
        if not text or len(text.strip()) < 10:
            print("❌ No se pudo extraer texto del CV o el texto es muy corto")
            return {}
        
        text = clean_text(text)
        print(f"✅ Texto extraído ({len(text)} caracteres)")
        
        # Extract phone information
        phone_code, phone_number = extract_phone(text)
        print(f"📞 Teléfono: {phone_code} {phone_number}")
        
        # Extract city
        city = extract_city(text, phone_code) if phone_code else ""
        print(f"🌆 Ciudad: {city}")
        
        # Extract name
        first_name, last_name = extract_full_name(text, city)
        print(f"👤 Nombre: {first_name} {last_name}")
        
        # Extract other information
        summary = extract_summary(text)
        professional_title = extract_prof_title(summary)
        education = extract_education(text)
        skills = extract_skills(text, SKILLS_KEYWORDS)
        experience = extract_experience(text)
        linkedin_url = extract_linkedin(text)
        portfolio_url = extract_portfolio(text)
        
        print("✅ CV analizado exitosamente")
        
        return {
            "first_name": first_name,
            "last_name": last_name,
            "phone_code": phone_code,
            "phone_number": phone_number,
            "city": city,
            "professional_title": professional_title,
            "summary": summary,
            "education": education,
            "skills": ", ".join(skills) if skills else "",
            "experience": experience,
            "linkedin_url": linkedin_url or "",
            "portfolio_url": portfolio_url,
        }
    except Exception as e:
        print(f"❌ Error inesperado en analyze_cv: {str(e)}")
        import traceback
        traceback.print_exc()
        raise