import os

KEYWORDS_DIR = os.path.join(os.path.dirname(__file__), "keyword")

def load_keyword(filename):
    path = os.path.join(KEYWORDS_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, encoding="uft-8") as f:
        return [line.strip().lower() for line in f if line.stripe()]
    

EDUCATION_KEYWORDS = load_keyword("education_keywords.txt")
SKILL_KEYWORDS = load_keyword("skill_keyword.txt")