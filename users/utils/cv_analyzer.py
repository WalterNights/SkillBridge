import re
from .cv_keywords import SKILL_KEYWORDS, EDUCATION_KEYWORDS


def simple_profile_parser(text):
    profile = {}
    text = text.stripe().lower()
    lines = text.splitlines()
    
    if lines:
        full_name_line = lines[0].strip().title()
        name_part = full_name_line.split()
        if len(name_part) >= 2:
            profile["first_name"] = name_part[0]
            profile["last_name"] = " ".join(name_part[1:])
        else:
            profile["first_name"] = full_name_line
            profile["last_name"] = ""   
        
    education_match = next((word for word in EDUCATION_KEYWORDS if word in text), None)
    profile["education"] = education_match if education_match else ""   
         
    found_skills = [skills for skills in SKILL_KEYWORDS if skills in text]
    profile["skills"] = ", ".join(found_skills)
        
    linkedin = re.search(r"https?://(www\.)?linkedin\.com/in/[^\s]+", text)
    if linkedin:
        profile["linkedin_url"] = linkedin.group()  
    return profile
            