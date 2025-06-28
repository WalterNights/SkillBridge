import fitz
import docx
import numpy as np
import pytesseract
from PIL import Image
import layoutparser as lp
from pdf2image import convert_from_bytes
from .cv_keywords import PROFFESIONAL_RESUME_KEYWORDS
  

def extract_layout_info_from_resume(file) -> dict:
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    profile_data = {}
    try:
        print("🔄 1. Convirtiendo PDF a imagen...")
        images = convert_from_bytes(
            file.read(),
            first_page=1,
            last_page=1,
            poppler_path=r'C:\poppler\poppler-24.08.0\Library\bin'
        )
        image = images[0]
        image_np = np.array(image)
        print("🔍 2. Ejecutando OCR layoutparser...")
        ocr_agent = lp.TesseractAgent(languages="spa")
        layout = ocr_agent.detect(image, return_response=True)
        layout = list(layout)
        if not layout or not hasattr(layout[0], "coordinates"):
            raise TypeError("El resultado del OCR no contiene bloques estructurados.")
        
        # todo este trozo de código no se ejecuta por que falla en el if anterior
        
        layout = sorted(layout, key=lambda b: b.coordinates[1])
        current_section = None
        summary_content = []
        for block in layout:
            segment_image = block.pad(left=5, right=5, top=5, bottom=5).crop_image(image_np)
            text = pytesseract.image_to_string(segment_image, lang="spa").strip()
            print(f"🧾 3. OCR detectado: {text}")
            if not text:
                continue
            if any(kw in text.lower() for kw in PROFFESIONAL_RESUME_KEYWORDS):
                current_section = "professional_title"
                profile_data["professional_title"] = text.split(":")[-1].strip()
            elif "educación" in text.lower():
                profile_data["education"] = text.split(":")[-1].strip()
            elif "experiencia" in text.lower():
                profile_data["experience"] = text.split(":")[-1].strip()
            elif "habilidades" in text.lower():
                profile_data["skills"] = text.split(":")[-1].strip()
            elif "linkedin" in text.lower():
                profile_data["linkedin_url"] = text.split(":")[-1].strip()
            elif "portafolio" in text.lower() or "portfolio" in text.lower():
                profile_data["portfolio_url"] = text.split(":")[-1].strip()
            elif "nombre" in text.lower():
                profile_data["first_name"] = text.split(":")[-1].strip()
            elif "apellido" in text.lower():
                profile_data["last_name"] = text.split(":")[-1].strip()      
            elif "teléfono" in text.lower() or "phone" in text.lower():
                profile_data["phone_number"] = text.split(":")[-1].strip()    
            elif "ciudad" in text.lower():
                profile_data["city"] = text.split(":")[-1].strip()
            elif current_section == "summary":
                summary_content.append(text)
        if summary_content:
            profile_data["summary"] = "\n".join(summary_content)
        return profile_data
    
    # y dispara esta excepción
    
    except TypeError as e:
        print(f"❌ 4. Error al procesar el layout: {e}")
        print("⚠️ 5. Usando OCR de toda la página como fallback...")
        text = pytesseract.image_to_string(image, lang="spa")
        print("📃 6. Texto OCR completo", text)
        return {"raw_text": text}
    except Exception as e:
        print(f"❌ 7. Error inesperado: {e}")
        raise RuntimeError("Failed to extract resume layout using Tesseract.")