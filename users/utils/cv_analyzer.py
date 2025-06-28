import re
from .cv_keywords import *


def find_keywords(text, keywords):
    return any(kw.lower() in text.lower() for kw in keywords)


def simple_profile_parser(text: str) -> dict:
    print("🔎 Tipo de input recibido:", type(text))
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text_joined = " ".join(lines)
    profile_data = {}
    # Full name extraction
    name_match = re.search(r"^(?P<first>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+(?P<last>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑa-záéíóúñ]+)?)", lines[0])
    if name_match:
        profile_data["first_name"] = name_match.group("first")
        profile_data["last_name"] = name_match.group("last")    
    # Phone number extraction
    phone_match = re.search(r"(?P<code>\+\d{1,3})[\s\-]?(?P<number>\d{7,10})", text_joined)
    if phone_match:
        profile_data["phone_code"] = phone_match.group(1)
        profile_data["phone_number"] = phone_match.group(2)      
    # Professional title extraction
    for line in lines:
        if find_keywords(line, PROFFESIONAL_RESUME_KEYWORDS):
            idx = lines.index(line) +1
            if idx < len(lines):
                full_title = lines[idx].strip()
                try:
                    title = re.match(r"^[A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+", full_title, re.IGNORECASE)
                    profile_data["professional_title"] = title.group(0) if title else full_title
                except Exception as e:
                    print(f"⚠️ Error extrayendo título profesional: {e}")
                    profile_data["professional_title"] = full_title
            break        
    # Profile summary extraction 
    summary_text = []
    capturing = False
    for line in lines:
        if find_keywords(line, PROFFESIONAL_RESUME_KEYWORDS):
            capturing = True
            continue
        if capturing and (find_keywords(line, EDUCATION_KEYWORDS + SKILL_KEYWORDS + EXPERIENCE_KEYWORDS)):
            break
        if capturing:
            summary_text.append(line)
    if summary_text:
        profile_data["summary"] = " ".join(summary_text).strip()
    # Education extraction
    education_text = []
    capturing = False
    for line in lines:
        if find_keywords(line, EDUCATION_KEYWORDS):
            capturing = True
            continue
        if capturing and find_keywords(line, SKILL_KEYWORDS + EXPERIENCE_KEYWORDS):
            break
        if capturing:
            education_text.append(line)
    if education_text:
        profile_data["education"] = " ".join(education_text).strip()    
    # Skills extraction
    skills_match = re.search(r"(?i)(Habilidades T[eé]cnicas|Skills)[:\-]?\s*(.*?)(?=\n|\Z)", text, re.DOTALL)
    if skills_match:
        profile_data["skills"] = skills_match.group(2).strip().replace("\n", ", ")
    # Experience extraction
    experience_text = []
    capturing = False
    for line in lines:
        if find_keywords(line, EXPERIENCE_KEYWORDS):
            capturing = True
            continue
        if capturing and find_keywords(line, SKILL_KEYWORDS + EDUCATION_KEYWORDS):
            break
        if capturing:
            experience_text.append(line)
    if experience_text:
        profile_data["experience"] = " ".join(experience_text).strip()
    # LinkedIn
    for line in lines:
        if find_keywords(line, LINKEDIN_KEYWORDS):
            linkedin_match = re.search(r"https?://[\w./-]*linkedin\.com/in/[\w-]+", line)
            if linkedin_match:
                profile_data["linkedin_url"] = linkedin_match.group(0)
    # Portfolio
    for line in lines:
        if find_keywords(line, PORTFOLIO_KEYWORDS):
            portfolio_match = re.search(r"https?://[\w./-]*portfolio[\w./-]*", line)
            if portfolio_match:
                profile_data["portfolio_url"] = portfolio_match.group(0)
    print(profile_data)
    return profile_data