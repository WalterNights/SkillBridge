import re
from .cv_keywords import SKILL_KEYWORDS, EDUCATION_KEYWORDS


def simple_profile_parser(resume_text):
    
    print("🔎 Tipo de input recibido:", type(resume_text))
    
    profile = {}
    text = resume_text.strip().lower()
    lines = text.splitlines()
    
    # Extracting the first line as full name
    if lines:
        full_name_line = lines[0].strip().title()
        name_part = full_name_line.split()
        if len(name_part) >= 2:
            profile["first_name"] = name_part[0]
            profile["last_name"] = " ".join(name_part[1:])
        else:
            profile["first_name"] = full_name_line
            profile["last_name"] = ""   
            
    # Extracting the phone number
    phone_match = re.search(r'tel[:\s]*\+?(\d[\d\s\-]+)', text, re.IGNORECASE)
    if phone_match:
        phone = phone_match.group(1).strip()
        if phone.startswith("57"):
            profile["phone_code"] = "+57"
            profile["phone_number"] = phone[2:].strip()
        elif phone.startswith("+"):
            profile["phone_code"] = phone.split()[0]
            profile["phone_number"] = " ".join(phone.split()[1:])
        else:
            profile["phone_code"] = ""
            profile["phone_number"] = phone
    else:
        profile["phone_code"] = ""
        profile["phone_number"] = ""
              
    # Extracting the city
    city_country_match = re.search(r'^(medell[ií]n),?\s*(colombia)?$', text, re.MULTILINE | re.IGNORECASE)
    profile["city"] = city_country_match.group(1).title() if city_country_match else ""
        
    # Extracting the education information
    collecting = False
    education_block = ""
    for line in lines:
        line = line.strip().lower()       
        if line.startswith("educación") or line.startswith("formación académica"):
            collecting = True
            continue
        if collecting:
            if any(
                line.startswith(header)
                for header in ["experiencia", "habilidades", "skills", "certificaciones", "resumen"]
            ):
                break
            education_block += line + " "
    profile["education"] = education_block.strip().title()      
     
    # Extracting the skills
    found_skills = [skills for skills in SKILL_KEYWORDS if skills in text]
    profile["skills"] = ", ".join(found_skills)
    
    # Extracting the experience
    experience_block = ""
    collecting = False
    for line in lines:
        line_lower = line.strip().lower()
        if line_lower.startswith("experiencia"):
            collecting = True
            continue
        if collecting:
            if any(
                line_lower.startswith(header)
                for header in ["educación", "formación", "habilidades", "skills", "certificaciones", "resumen"]
            ):
                break
            experience_block += line.strip() + "\n"
    profile["experience"] = experience_block.strip().title()
        
    # Extracting the LinkedIn URL
    linkedin = re.search(r"https?://(www\.)?linkedin\.com/in/[^\s]+", text)
    if linkedin:
        profile["linkedin_url"] = linkedin.group()
        
    return profile
            