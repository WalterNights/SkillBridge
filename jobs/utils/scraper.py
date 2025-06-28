import requests, re
from bs4 import BeautifulSoup
from jobs.models import JobOffer
from django.utils import timezone
from jobs.keywords import COMMON_KEYWORDS


def scrap_computrabajo(query="desarrollador", location="colombia"):
    base_url = f"https://co.computrabajo.com/trabajo-de-{query}?p="
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/114.0.0.0 Safari/537.36"
    }
    offers = []
    for page in range(1, 3):
        url = base_url + str(page)
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, "html.parser")
        articles = soup.find_all("article", class_="box_offer")
        print(f"Ofertas encontradas en página {page}: {len(articles)}")
        with open("output.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        for article in articles:
            try:
                title_tag = article.select_one("a.js-o-link")
                company_tag = article.select_one("p.fs16.fc_base.mt5")
                location_tag = article.find_all("p")[1] if len(article.find_all("p")) > 1 else None
                title = title_tag.get_text(strip=True) if title_tag else ""
                job_url = "https://co.computrabajo.com" + title_tag["href"] if title_tag else ""
                company = company_tag.get_text(strip=True) if company_tag else ""
                location = location_tag.get_text(strip=True) if location_tag else ""
                description, requirements, keywords = get_offer_summary(job_url)
                summary = f"{description}\n\nREQUISITOS:\n{requirements}" if requirements else description
                obj, created = JobOffer.objects.get_or_create(
                    url=job_url,
                    defaults={
                        "title": title,
                        "company": company,
                        "location": location,
                        "summary": summary,
                        "keywords": keywords,
                        "url": job_url
                    }
                )
                if created:
                    offers.append(obj)  
            except Exception as e:
                print("Error en tarjeta:", e)        
    print(f"{len(offers)} ofertas agregadas.")
    return offers


def extract_keywords(text):
    text = text.lower().replace(".net core", ".net").replace("c ", "c# ")
    found_keywords = [
        kw for kw in COMMON_KEYWORDS
        if re.search(r'\b' + re.escape(kw) + r'\b', text)
        ]  
    return ', '.join(found_keywords)


def run_scraper_and_store_results(query):
    print(f"Ejecutando Scrap con query: {query}")
    return scrap_computrabajo(query=query)


def get_offer_summary(offer_url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        response = requests.get(offer_url, headers=headers)
        soup = BeautifulSoup(response.content, "html.parser")
        description_title = soup.find("h3", string=lambda text: text and "descripción" in text.lower())
        if not description_title:
            print("No se encontró el título de la descripción.")
            return "", "", ""
        all_text = []
        for sibling in description_title.find_next_siblings():
            if sibling.name == "h3":
                break
            if sibling.name == "p" or sibling.name == "li":
                all_text.append(sibling.get_text(strip=True))       
        full_text = "\n".join(all_text)
        split_keywords = ["requisitos", "habilidades", "condiciones", "te ofrecemos", "perfil", "ofrecemos", "conocimientos", "skills", "qué harás", "responsabilidades"]
        split_point = -1
        for keyword in split_keywords:
            pattern = re.compile(keyword, re.IGNORECASE)
            match = pattern.search(full_text)
            if match:
                split_point = match.start()
                break
        if split_point != -1:
            description = full_text[:split_point].strip()
            requirements = full_text[split_point:].strip()
        else:
            description = full_text
            requirements = ""  
        keywords = extract_keywords(requirements)      
        return description, requirements, keywords
    except Exception as e:
        print("Error obteniendo resumen:", e)
        return "", "", ""