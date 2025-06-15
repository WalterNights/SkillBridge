import requests
from bs4 import BeautifulSoup
from jobs.models import JobOffer
from django.utils import timezone


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
        
        print("===> 1 Status code:", response.status_code)
        print("===> 2 URL final (redirecciones):", response.url)
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        articles = soup.find_all("article", class_="box_offer")
        
        print("===> 3 Página descargada:", url)
        print("===> 4 Longitud HTML:", len(soup.prettify()))
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
                summary = get_offer_summary(job_url)
                
                obj, created = JobOffer.objects.get_or_create(
                    url=job_url,
                    defaults={
                        "title": title,
                        "company": company,
                        "location": location,
                        "summary": summary,
                        "keywords": extract_keywords(title + " " + company + " " + summary)
                    }
                )
                if created:
                    offers.append(obj)
                    
            except Exception as e:
                print("Error en tarjeta:", e)
                
    print(f"{len(offers)} ofertas agregadas.")
    
    return offers


def extract_keywords(text):
    common_keywords = [
        'python', 'javascript', 'sql', 'excel', 'django', 'react', 'angular',
        'flask', 'node', 'typescript', 'aws', 'docker', 'git', 'rest', 'api',
        'comercial', 'ventas', 'negocios', 'marketing'
    ]
    return ', '.join([kw for kw in common_keywords if kw in text.lower()])


def run_scraper_and_store_results(query):
    print(f"Ejecutando Scrap con query: {query}")
    return scrap_computrabajo(query=query)


def get_offer_summary(offer_url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    
    try:
        response = requests.get(offer_url, headers=headers)
        
        print("===> 5 Summary URL:", response.url)
        print("===> 6 Summary Status Code:", response.status_code)
        
        file_name = "detalle_oferta.html"
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"HTML de oferta guardado en: {file_name}")
        
        soup = BeautifulSoup(response.content, "html.parser")
        description_tag = soup.select_one(".box_offer_detail")
        return description_tag.get_text(strip=True) if description_tag else ""
    
    except Exception as e:
        print("Error obteniendo resumen:", e)
        return ""