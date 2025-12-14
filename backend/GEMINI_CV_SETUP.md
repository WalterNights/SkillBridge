# Configuración del Análisis de CV con Gemini AI

## Descripción

El sistema de análisis de CV ha sido refactorizado para utilizar **Google Gemini AI** (modelo `gemini-2.0-flash-exp`) en lugar del sistema tradicional basado en regex y keywords.

## Ventajas de usar Gemini AI

✅ **Mayor precisión**: Análisis inteligente del contenido del CV  
✅ **Mejor extracción**: Comprende el contexto y no solo patrones  
✅ **Multi-idioma**: Funciona con CVs en diferentes idiomas  
✅ **Resumen automático**: Genera resúmenes profesionales coherentes  
✅ **Adaptabilidad**: Se adapta a diferentes formatos de CV  

## Configuración

### 1. Variables de Entorno

Asegúrate de que la API Key de Gemini esté configurada en el archivo `.env`:

```env
GEMINI_API_KEY=tu_api_key_aqui
```

### 2. Instalación de Dependencias

Instala la nueva dependencia de Google Generative AI:

```bash
cd backend
pip install -r requirements.txt
```

O instala directamente:

```bash
pip install google-generativeai==0.8.3
```

### 3. Obtener API Key de Gemini

1. Visita [Google AI Studio](https://aistudio.google.com/apikey)
2. Crea o selecciona un proyecto
3. Genera una nueva API Key
4. Copia la clave y agrégala al archivo `.env`

## Arquitectura

### Componentes Principales

#### 1. `GeminiCVService` (nuevo)
**Ubicación**: `backend/users/services/gemini_cv_service.py`

Servicio principal que maneja el análisis de CVs usando Gemini AI.

**Métodos principales**:
- `analyze_cv(cv_file)`: Analiza el CV y retorna datos estructurados
- `extract_text_from_file(cv_file)`: Extrae texto de PDF/DOCX
- `validate_cv_file(cv_file)`: Valida formato y tamaño del archivo

#### 2. `AnalyzerResumeView` (actualizado)
**Ubicación**: `backend/users/views.py`

Vista API que recibe el CV del frontend y usa `GeminiCVService` para procesarlo.

**Endpoint**: `POST /users/analyzer-cv/`

#### 3. `analyze_cv_async` (actualizado)
**Ubicación**: `backend/users/tasks.py`

Tarea asíncrona de Celery para análisis en segundo plano.

## Formato de Datos Extraídos

El servicio retorna un diccionario con la siguiente estructura:

```python
{
    "first_name": str,           # Nombre
    "last_name": str,            # Apellido
    "full_name": str,            # Nombre completo
    "phone_code": str,           # Código de país (ej: "+57")
    "phone_number": str,         # Número sin código
    "country": str,              # País
    "city": str,                 # Ciudad
    "professional_title": str,   # Título profesional/rol
    "summary": str,              # Resumen profesional
    "skills": str,               # Skills separadas por comas
    "education": str,            # Resumen de educación
    "experience": str,           # Resumen de experiencia
    "linkedin_url": str,         # URL de LinkedIn
    "portfolio_url": str         # URL de portafolio/GitHub
}
```

## Uso

### Desde el Frontend

El componente `profile.component.ts` ya está configurado para usar el endpoint:

```typescript
this.http.post('http://localhost:8000/users/analyzer-cv/', formData)
  .subscribe({
    next: (response) => {
      // Datos extraídos del CV
      console.log(response);
    },
    error: (error) => {
      console.error('Error:', error);
    }
  });
```

### Formatos Soportados

- ✅ PDF (.pdf)
- ✅ DOCX (.docx)

**Tamaño máximo**: 10MB

## Prompt de Gemini

El servicio usa un prompt estructurado que instruye a Gemini a:

1. Analizar el CV de forma exhaustiva
2. Extraer solo información presente (no inventar)
3. Retornar un JSON válido con estructura específica
4. Generar un resumen profesional conciso
5. Identificar skills técnicas relevantes

## Manejo de Errores

El servicio maneja varios tipos de errores:

- ❌ **Archivo no válido**: Formato no soportado o archivo vacío
- ❌ **Archivo muy grande**: Supera el límite de 10MB
- ❌ **API Key no configurada**: GEMINI_API_KEY no encontrada
- ❌ **Error de parsing**: Respuesta de Gemini no es JSON válido
- ❌ **Texto insuficiente**: CV tiene menos de 50 caracteres

## Logging

El servicio registra información detallada:

```python
logger.info("Enviando CV a Gemini para análisis...")
logger.info(f"CV analizado exitosamente: {full_name}")
logger.error(f"Error en análisis de CV: {error}")
```

## Comparación con Sistema Anterior

| Característica | Sistema Anterior | Gemini AI |
|----------------|------------------|-----------|
| Método | Regex + Keywords | IA Generativa |
| Precisión | Media-Baja | Alta |
| Idiomas | Solo español | Multi-idioma |
| Formatos CV | Limitado | Adaptable |
| Resumen | Extracción literal | Generado inteligente |
| Mantenimiento | Alto (actualizar reglas) | Bajo (modelo se adapta) |

## Costos

- Google Gemini API tiene una capa gratuita generosa
- Modelo `gemini-2.0-flash-exp` es optimizado para velocidad y costo
- Para producción, revisa los [precios de Gemini](https://ai.google.dev/pricing)

## Migración

### Sistema Antiguo (todavía disponible)

Si necesitas volver al sistema anterior, los archivos originales están en:
- `users/utils/cv_analyzer.py`
- `users/services/cv_analyzer_service.py`

Solo cambia el import en `views.py`:

```python
# Gemini (actual)
from users.services.gemini_cv_service import GeminiCVService

# Sistema anterior
from users.services.cv_analyzer_service import CVAnalyzerService
```

## Testing

Para probar el servicio:

```python
from users.services.gemini_cv_service import GeminiCVService

# Crear instancia
service = GeminiCVService()

# Analizar CV
with open('path/to/cv.pdf', 'rb') as f:
    result = service.analyze_cv(f)
    print(result)
```

## Troubleshooting

### Error: "GEMINI_API_KEY no encontrada"
- Verifica que el archivo `.env` contenga `GEMINI_API_KEY=...`
- Reinicia el servidor Django después de agregar la variable

### Error: "No se pudo parsear la respuesta"
- Gemini puede retornar texto no estructurado si el CV es muy corto
- Verifica que el CV tenga contenido suficiente (>50 caracteres)

### Error: "Rate limit exceeded"
- Has excedido el límite de la API gratuita
- Espera unos minutos o actualiza a un plan de pago

## Roadmap

Mejoras futuras planeadas:

- [ ] Soporte para análisis de múltiples CVs en batch
- [ ] Cache de resultados para CVs idénticos
- [ ] Soporte para imágenes (OCR integrado)
- [ ] Análisis de match con ofertas de trabajo
- [ ] Dashboard de estadísticas de análisis

## Contacto y Soporte

Para reportar bugs o sugerir mejoras, contacta al equipo de desarrollo.
