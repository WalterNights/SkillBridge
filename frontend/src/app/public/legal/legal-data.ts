/**
 * Contenido legal estático de SkilTak.
 *
 * Privacy + Terms + Cookies en español, adaptados a:
 *   - Ley 1581/2012 (Habeas Data) y Decreto 1377/2013 de Colombia
 *   - Mención GDPR para usuarios EU
 *   - Realidad del producto: scraping de portales públicos, OAuth con
 *     LinkedIn, análisis de CV con Gemini, alertas por email
 *
 * Si el contenido crece mucho o se necesita versionar (regulatorio),
 * mover a markdown estático + parser. Por ahora — strings es suficiente.
 */

export type LegalSection = {
  /** Heading visible (h2). */
  heading: string;
  /** Anchor para que se pueda linkear desde fuera (#contacto, etc). */
  anchor: string;
  /** Párrafos del cuerpo. Renderizados en orden, uno por <p>. */
  body: string[];
  /** Bullets opcionales debajo del body. */
  bullets?: string[];
};

export type LegalDoc = {
  slug: 'privacidad' | 'terminos' | 'cookies';
  title: string;
  /** Subtítulo que sale debajo del title — usualmente fecha + jurisdicción. */
  subtitle: string;
  /** Versionado humano + fecha — sale en el header y al pie. */
  lastUpdated: string;
  /** Tagline corto para meta description / SEO. */
  excerpt: string;
  sections: LegalSection[];
};

const PRIVACIDAD: LegalDoc = {
  slug: 'privacidad',
  title: 'Política de Privacidad',
  subtitle: 'Cómo SkilTak recolecta, usa y protege tus datos personales.',
  lastUpdated: '23 de junio de 2026',
  excerpt:
    'Política de Privacidad de SkilTak conforme a la Ley 1581/2012 (Habeas Data) de Colombia y al GDPR para usuarios de la Unión Europea.',
  sections: [
    {
      heading: '1. Quiénes somos',
      anchor: 'quienes-somos',
      body: [
        'SkilTak es una plataforma de búsqueda de empleo que agrega ofertas públicas de múltiples portales y las cruza con el perfil profesional del usuario para sugerir las que mejor coinciden. El responsable del tratamiento de tus datos es el equipo de SkilTak, contactable en privacy@skiltak.com.',
        'Esta política aplica a todo el contenido y los servicios disponibles en skiltak.com, api.skiltak.com y subdominios relacionados.',
      ],
    },
    {
      heading: '2. Qué datos recolectamos',
      anchor: 'datos',
      body: [
        'Recolectamos únicamente los datos necesarios para operar el servicio y mejorar la calidad de los matches. Específicamente:',
      ],
      bullets: [
        'Datos de cuenta: nombre de usuario, correo electrónico, contraseña (almacenada en forma cifrada con un algoritmo de hashing irreversible).',
        'Datos de perfil profesional: ciudad, título actual, años de experiencia, habilidades técnicas y blandas, idiomas, modalidad preferida (remoto, presencial, híbrido).',
        'CV: el archivo que subes y los datos estructurados que extraemos de él (experiencia, formación, logros). El archivo se almacena cifrado en reposo.',
        'Datos de actividad: postulaciones que marcas, estados de seguimiento, notas privadas, preferencias de alertas.',
        'Datos de autenticación con terceros: si decides iniciar sesión con LinkedIn, recibimos tu identificador público de LinkedIn, nombre y correo verificado. Nunca recibimos tu contraseña de LinkedIn ni accedemos a tus contactos o publicaciones.',
        'Datos técnicos: dirección IP, navegador, sistema operativo y páginas visitadas dentro de SkilTak, con fines de seguridad y prevención de abuso.',
      ],
    },
    {
      heading: '3. Para qué los usamos',
      anchor: 'finalidad',
      body: [
        'Usamos tus datos exclusivamente para los fines que detallamos a continuación. No los vendemos ni los entregamos a redes publicitarias.',
      ],
      bullets: [
        'Generar tu lista personalizada de ofertas con un porcentaje de match calculado contra tu perfil.',
        'Enviarte alertas por correo cuando aparecen ofertas con alto match (solo si activaste esta opción en Configuración).',
        'Analizar tu CV con un modelo de inteligencia artificial para sugerir mejoras de redacción, estructura y palabras clave.',
        'Permitirte hacer seguimiento de tus postulaciones (pendiente, postulada, en revisión, entrevista, oferta, rechazada).',
        'Detectar y bloquear actividad maliciosa, fraude o abuso del servicio.',
        'Cumplir con obligaciones legales aplicables.',
      ],
    },
    {
      heading: '4. Terceros con los que compartimos datos',
      anchor: 'terceros',
      body: [
        'Algunos servicios externos procesan datos en nuestro nombre. En todos los casos firmamos o aceptamos cláusulas que garantizan un tratamiento conforme a esta política:',
      ],
      bullets: [
        'Google Cloud (Gemini API): cuando analizamos tu CV o generamos sugerencias por IA, el texto del CV se envía a la API de Gemini. Google no usa estos datos para entrenar sus modelos según los términos de su API empresarial.',
        'LinkedIn: si eliges iniciar sesión con LinkedIn, intercambiamos un token de autorización con LinkedIn para verificar tu identidad. No publicamos nada en tu nombre.',
        'Proveedor de hosting (Hostinger): aloja la infraestructura del backend y base de datos en servidores ubicados en Europa.',
        'Proveedor de email (SMTP de Google Workspace): entrega los correos transaccionales y de alertas que te enviamos.',
      ],
    },
    {
      heading: '5. Ofertas de empleo y datos de terceros',
      anchor: 'ofertas',
      body: [
        'Las ofertas de empleo que ves en SkilTak provienen de portales públicos (LinkedIn, Indeed, Magneto, Computrabajo, entre otros). Las recopilamos automáticamente desde sus páginas públicas y mostramos un resumen junto con un enlace al portal original.',
        'No enviamos tus datos personales a estos portales cuando te mostramos sus ofertas. Si decides postularte, te redirigimos al portal de origen y la postulación ocurre fuera de SkilTak, sujeta a la política de privacidad de ese portal.',
      ],
    },
    {
      heading: '6. Cuánto tiempo guardamos tus datos',
      anchor: 'retencion',
      body: [
        'Conservamos tus datos mientras tu cuenta esté activa. Si solicitas eliminar tu cuenta, borramos tus datos personales en un plazo máximo de 30 días, salvo aquellos que estemos obligados a conservar por ley (por ejemplo, registros de seguridad pueden retenerse hasta 12 meses).',
        'Las ofertas de empleo que coinciden con tu perfil se almacenan agregadas (sin asociarse a tu cuenta una vez expiradas) por hasta 90 días para análisis estadísticos internos.',
      ],
    },
    {
      heading: '7. Tus derechos',
      anchor: 'derechos',
      body: [
        'Como titular de tus datos personales, tienes derecho a:',
      ],
      bullets: [
        'Acceder a los datos que tenemos sobre ti.',
        'Rectificar datos inexactos o desactualizados.',
        'Solicitar la eliminación de tu cuenta y tus datos (derecho al olvido).',
        'Oponerte al tratamiento con fines no esenciales (por ejemplo, desactivar las alertas por correo).',
        'Solicitar la portabilidad de tus datos en un formato estructurado (JSON o CSV).',
        'Revocar el consentimiento en cualquier momento.',
        'Presentar un reclamo ante la Superintendencia de Industria y Comercio de Colombia, o la autoridad de protección de datos competente en tu país.',
      ],
    },
    {
      heading: '8. Seguridad',
      anchor: 'seguridad',
      body: [
        'Aplicamos medidas técnicas y organizativas razonables para proteger tus datos: cifrado HTTPS en todas las comunicaciones, contraseñas hasheadas con bcrypt, cifrado en reposo del CV y la base de datos, control de accesos con principio de mínimo privilegio, logs de auditoría y monitoreo de actividad anómala.',
        'Ningún sistema es completamente invulnerable. Si detectamos una violación de datos que pueda afectarte, te notificaremos por correo dentro de las 72 horas posteriores al hallazgo, conforme exige el GDPR.',
      ],
    },
    {
      heading: '9. Transferencias internacionales',
      anchor: 'transferencias',
      body: [
        'Algunos de nuestros proveedores (Google Cloud para Gemini, Hostinger para hosting) procesan datos fuera de Colombia. Estas transferencias se realizan bajo cláusulas contractuales tipo aprobadas por la Comisión Europea, o hacia jurisdicciones reconocidas con nivel adecuado de protección.',
      ],
    },
    {
      heading: '10. Menores de edad',
      anchor: 'menores',
      body: [
        'SkilTak no está dirigido a menores de 16 años. No recolectamos a sabiendas datos personales de menores. Si descubrimos que recolectamos datos de un menor sin consentimiento parental verificable, eliminaremos esos datos de inmediato.',
      ],
    },
    {
      heading: '11. Cambios a esta política',
      anchor: 'cambios',
      body: [
        'Podemos actualizar esta política para reflejar cambios en el producto o en la regulación. Si hacemos cambios materiales, te avisaremos por correo o mediante un aviso destacado en la plataforma con al menos 15 días de antelación.',
        'La versión vigente siempre estará en esta página, con la fecha de última actualización al pie.',
      ],
    },
    {
      heading: '12. Contacto',
      anchor: 'contacto',
      body: [
        'Para ejercer tus derechos, hacer preguntas o reportar una inquietud sobre el tratamiento de tus datos, escríbenos a privacy@skiltak.com. Respondemos en un plazo máximo de 15 días hábiles.',
      ],
    },
  ],
};

const TERMINOS: LegalDoc = {
  slug: 'terminos',
  title: 'Términos y Condiciones',
  subtitle: 'Reglas de uso de la plataforma SkilTak.',
  lastUpdated: '23 de junio de 2026',
  excerpt:
    'Términos y Condiciones de uso de SkilTak. Al crear una cuenta aceptas estas reglas.',
  sections: [
    {
      heading: '1. Aceptación',
      anchor: 'aceptacion',
      body: [
        'Al crear una cuenta o usar SkilTak aceptas estos Términos y Condiciones y la Política de Privacidad. Si no estás de acuerdo con alguna parte, no debes usar el servicio.',
        'Estos términos pueden actualizarse. Te notificaremos cambios materiales con 15 días de antelación.',
      ],
    },
    {
      heading: '2. Qué ofrece SkilTak',
      anchor: 'servicio',
      body: [
        'SkilTak es una plataforma que agrega ofertas de empleo públicas de múltiples portales y las muestra rankeadas según el match con el perfil de cada usuario. También ofrece herramientas de análisis de CV y seguimiento de postulaciones.',
        'SkilTak no es un empleador ni un intermediario laboral. No participamos en el proceso de contratación entre tú y las empresas. Las ofertas que mostramos son de terceros y la postulación ocurre en el portal de origen.',
      ],
    },
    {
      heading: '3. Cuenta de usuario',
      anchor: 'cuenta',
      body: [
        'Para usar las funciones principales tienes que crear una cuenta. Eres responsable de:',
      ],
      bullets: [
        'Mantener la confidencialidad de tu contraseña.',
        'Proporcionar información veraz y actualizada en tu perfil.',
        'Notificarnos cualquier uso no autorizado de tu cuenta.',
        'Tener al menos 16 años de edad.',
      ],
    },
    {
      heading: '4. Uso aceptable',
      anchor: 'uso',
      body: [
        'No puedes usar SkilTak para:',
      ],
      bullets: [
        'Hacer scraping automatizado de nuestros datos o reutilizarlos en otro servicio sin autorización escrita.',
        'Crear múltiples cuentas para evadir límites o sanciones.',
        'Subir contenido falso, ofensivo, ilegal o que infrinja derechos de terceros.',
        'Intentar comprometer la seguridad de la plataforma (ataques, ingeniería inversa, escaneo de vulnerabilidades sin autorización).',
        'Usar el servicio para fines comerciales no autorizados (por ejemplo, publicidad masiva o reclutamiento sin nuestro acuerdo).',
      ],
    },
    {
      heading: '5. Datos de empleo de terceros',
      anchor: 'datos-terceros',
      body: [
        'Las ofertas de empleo que mostramos provienen de portales públicos. SkilTak no garantiza que estas ofertas estén vigentes, sean reales o cumplan con las descripciones publicadas en el portal de origen.',
        'Te recomendamos verificar siempre la información directamente con el empleador antes de tomar decisiones (renunciar a otro empleo, mudarte, pagar tasas, etc.).',
      ],
    },
    {
      heading: '6. Análisis con inteligencia artificial',
      anchor: 'ia',
      body: [
        'Las funciones de análisis de CV y sugerencias usan modelos de IA de terceros (actualmente Google Gemini). Los resultados son orientativos y no constituyen asesoría profesional vinculante.',
        'Tú eres responsable de revisar y editar cualquier sugerencia antes de aplicarla. SkilTak no se responsabiliza por decisiones tomadas únicamente con base en sugerencias automáticas.',
      ],
    },
    {
      heading: '7. Propiedad intelectual',
      anchor: 'propiedad',
      body: [
        'El código, diseño, marca, logo y contenido editorial de SkilTak son propiedad nuestra o de nuestros licenciantes. No puedes copiar, modificar ni redistribuir nuestro contenido sin autorización escrita.',
        'Tú retienes la propiedad sobre el contenido que subes (CV, datos de perfil). Nos otorgas una licencia limitada para procesarlo con el único fin de operar el servicio.',
      ],
    },
    {
      heading: '8. Disponibilidad y modificaciones',
      anchor: 'disponibilidad',
      body: [
        'Hacemos esfuerzos razonables para mantener el servicio disponible, pero no garantizamos un uptime del 100%. Podemos suspender temporalmente partes del servicio para mantenimiento o actualizaciones.',
        'Podemos modificar, suspender o discontinuar funcionalidades en cualquier momento. Si una modificación afecta materialmente tu uso del servicio, te avisaremos con antelación razonable.',
      ],
    },
    {
      heading: '9. Limitación de responsabilidad',
      anchor: 'responsabilidad',
      body: [
        'En la máxima medida permitida por la ley aplicable, SkilTak no se hace responsable por daños indirectos, lucro cesante, pérdida de oportunidades laborales o cualquier perjuicio derivado del uso del servicio.',
        'Nuestra responsabilidad total acumulada hacia ti por cualquier reclamo relacionado con el servicio no excederá el equivalente al monto que hayas pagado por el servicio en los 12 meses anteriores al hecho que da origen al reclamo. Si el servicio fue gratuito, esta responsabilidad se limita a USD 50.',
      ],
    },
    {
      heading: '10. Suspensión y cancelación',
      anchor: 'cancelacion',
      body: [
        'Puedes cancelar tu cuenta en cualquier momento desde Configuración. La cancelación elimina tus datos personales según lo descrito en la Política de Privacidad.',
        'Podemos suspender o cancelar tu cuenta sin previo aviso si detectamos violaciones a estos términos, especialmente por abuso, fraude o uso comercial no autorizado.',
      ],
    },
    {
      heading: '11. Ley aplicable y jurisdicción',
      anchor: 'jurisdiccion',
      body: [
        'Estos términos se rigen por las leyes de la República de Colombia. Cualquier disputa será resuelta en los tribunales competentes de Colombia.',
        'Si vives en la Unión Europea, mantienes los derechos no renunciables que te otorga la legislación de tu país de residencia.',
      ],
    },
    {
      heading: '12. Contacto',
      anchor: 'contacto',
      body: [
        'Para cualquier consulta sobre estos términos, escríbenos a legal@skiltak.com.',
      ],
    },
  ],
};

const COOKIES: LegalDoc = {
  slug: 'cookies',
  title: 'Política de Cookies',
  subtitle: 'Qué cookies usamos y para qué.',
  lastUpdated: '23 de junio de 2026',
  excerpt:
    'Cookies que SkilTak usa para autenticación, preferencias y métricas anónimas.',
  sections: [
    {
      heading: '1. Qué son las cookies',
      anchor: 'que-son',
      body: [
        'Las cookies son pequeños archivos de texto que un sitio web guarda en tu navegador. Sirven para recordar tu sesión, tus preferencias y para medir el uso del servicio.',
      ],
    },
    {
      heading: '2. Cookies que usamos',
      anchor: 'usamos',
      body: [
        'SkilTak usa únicamente las cookies estrictamente necesarias para operar el servicio. No usamos cookies de publicidad ni de seguimiento entre sitios.',
      ],
      bullets: [
        'Cookies de sesión y autenticación: para mantenerte logueado entre páginas. Si activas "Mantener sesión iniciada" se almacenan en localStorage; si no, se borran al cerrar la pestaña.',
        'Cookies de preferencias: para recordar tu elección de "remember me" y configuraciones de la interfaz.',
        'Cookies de seguridad: tokens CSRF para prevenir ataques de falsificación de solicitudes.',
      ],
    },
    {
      heading: '3. Cookies de terceros',
      anchor: 'terceros',
      body: [
        'Cuando usas "Iniciar sesión con LinkedIn", LinkedIn puede establecer cookies en su propio dominio durante el proceso de OAuth. Esas cookies se rigen por la política de LinkedIn.',
        'Actualmente no usamos servicios de analytics de terceros (Google Analytics, Hotjar, etc.). Si en el futuro los incorporamos, actualizaremos esta política y solicitaremos tu consentimiento explícito cuando corresponda.',
      ],
    },
    {
      heading: '4. Cómo controlar las cookies',
      anchor: 'control',
      body: [
        'Puedes borrar las cookies desde la configuración de tu navegador. Ten en cuenta que si borras las cookies de sesión, tendrás que volver a iniciar sesión.',
        'Si bloqueas todas las cookies, algunas funciones del servicio (como mantenerte logueado) dejarán de funcionar.',
      ],
    },
    {
      heading: '5. Contacto',
      anchor: 'contacto',
      body: [
        'Para preguntas sobre el uso de cookies, escríbenos a privacy@skiltak.com.',
      ],
    },
  ],
};

export const LEGAL_DOCS: LegalDoc[] = [PRIVACIDAD, TERMINOS, COOKIES];

export function findLegalBySlug(slug: string): LegalDoc | undefined {
  return LEGAL_DOCS.find((doc) => doc.slug === slug);
}
