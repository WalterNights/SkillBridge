/**
 * Catálogo de artículos del /recursos. Hardcoded en TS porque:
 *   - Son pocos (3 ahora, 8-10 a futuro).
 *   - Versionar en git da mejor traceability que un CMS para este tamaño.
 *   - El parser de Markdown sería overhead innecesario para texto curado.
 *
 * Cuando pasemos los 15-20 artículos, migrar a una colección backend +
 * editor markdown. Por ahora, mantener simple.
 */

export interface ArticleSection {
  heading: string;
  body: string[]; // párrafos
  bullets?: string[]; // lista opcional al final
  /** Cita destacada después de los bullets/body. Sin attribución. */
  callout?: string;
}

export interface Article {
  slug: string;
  category: string; // "Guía" | "Reporte" | etc.
  readMinutes: number;
  title: string;
  excerpt: string;
  /** Intro: párrafos sin heading, antes de las secciones. */
  intro: string[];
  sections: ArticleSection[];
  /** Conclusión opcional al final. */
  closing?: string[];
}


export const ARTICLES: readonly Article[] = [
  // ============================================================
  // CV ATS 2026
  // ============================================================
  {
    slug: 'cv-ats-2026',
    category: 'Guía',
    readMinutes: 7,
    title: 'Cómo escribir un CV que pase ATS en 2026',
    excerpt:
      'La estructura, los keywords y los errores que te dejan fuera del primer filtro automatizado.',
    intro: [
      'El primer filtro de tu CV no lo hace una persona — lo hace un software llamado Applicant Tracking System (ATS). Estos sistemas escanean tu documento buscando palabras clave, miden coincidencias contra la descripción del puesto, y le dan al reclutador solo el subconjunto que pasa el umbral. Si tu CV no está optimizado para ATS, nunca llega a ojos humanos.',
      'La buena noticia: las reglas para pasar son sencillas y aplican a cualquier profesión. Acá va el playbook.',
    ],
    sections: [
      {
        heading: 'Usa la estructura más simple posible',
        body: [
          'Los ATS leen tu CV de arriba abajo, en una sola columna. Cuando metes diseños creativos con dos columnas, tablas anidadas o cuadros de texto, el parser se pierde y rescata fragmentos sin orden.',
        ],
        bullets: [
          'Una sola columna. Sin layouts en grid ni tabular.',
          'Encabezados estándar: "Experiencia", "Educación", "Habilidades". El parser los reconoce por nombre.',
          'Sin imágenes, iconos ni logos. Si los pones, el ATS los ignora pero te resta puntos de legibilidad.',
          'Formato PDF (no .docx). El PDF preserva tipografía y estructura entre versiones; .docx puede mutar.',
        ],
      },
      {
        heading: 'Copia las palabras clave de la oferta literal',
        body: [
          'Si el job description dice "JavaScript", no escribas "JS". Si dice "gestión de proyectos", no pongas "project management". Los ATS hacen matching exacto de tokens, no entienden sinónimos por default.',
          'Lee la oferta dos veces antes de personalizar tu CV. Identifica las 8-12 palabras clave que se repiten. Asegúrate de que aparezcan en tu CV, idealmente en el contexto donde demuestras la habilidad (no solo listadas en "Skills").',
        ],
        callout:
          'Personalizar el CV por oferta toma 10 minutos. La diferencia en tasa de respuesta es 3x.',
      },
      {
        heading: 'La longitud importa',
        body: [
          'No hay regla universal, pero sí una guía sólida: una página si tienes menos de 7 años de experiencia, dos páginas si tienes más. Tres páginas o más es overkill — el reclutador no las lee.',
          'Recortar es difícil pero crítico. Pregúntate por cada bullet: "¿esto cambia la decisión del reclutador?". Si la respuesta es no, fuera.',
        ],
      },
      {
        heading: 'Cuantifica los logros',
        body: [
          'El cerebro humano (y los rankings que los ATS aplican) le presta más atención a números que a adjetivos. Compara:',
          '"Mejoré el rendimiento del equipo" vs "Reduje el tiempo de entrega de proyectos de 6 a 4 semanas".',
          'Siempre que puedas, agrega: porcentajes, cantidades, plazos, presupuestos. Si no tienes números exactos, estima con orden de magnitud — es mejor "decenas de clientes" que ningún número.',
        ],
      },
      {
        heading: 'Los 5 errores que te dejan fuera',
        body: ['Si haces alguno de estos, ningún ATS te aprueba. En orden de gravedad:'],
        bullets: [
          'CV en imagen (foto del PDF). El ATS no lee texto dentro de imágenes.',
          'Tipografías exóticas. Stick con Arial, Calibri, Helvetica, Times. Decorativas se renderean como cuadritos.',
          'Encabezados creativos. "Mi viaje profesional" en vez de "Experiencia" rompe el parser.',
          'Información personal innecesaria. Estado civil, número de hijos, edad — no aportan, ocupan espacio.',
          'Errores ortográficos. El ATS los flagea automáticamente; el reclutador se cae del proceso si los detecta.',
        ],
      },
    ],
    closing: [
      'Tu CV optimizado para ATS sigue siendo legible y atractivo para humanos. La idea no es escribir para robots: es no escribir CONTRA ellos.',
      'Cuando termines, súbelo a SkilTak — analizamos la estructura y te decimos qué mejorar antes de aplicar a la primera oferta.',
    ],
  },

  // ============================================================
  // Skills Latam 2026
  // ============================================================
  {
    slug: 'skills-latam-2026',
    category: 'Reporte',
    readMinutes: 9,
    title: 'Las 12 skills más buscadas en Latam (2026)',
    excerpt:
      'Analizamos +50,000 ofertas para entender hacia dónde se mueve el mercado regional. Distribución por sector.',
    intro: [
      'Cada noche SkilTak escanea miles de ofertas en LinkedIn, Computrabajo, Magneto, Indeed y otros. Esto nos da una vista privilegiada del mercado: qué skills aparecen más, en qué sectores, y cómo va evolucionando la demanda.',
      'Este reporte mira los últimos 90 días de scraping (~50,000 ofertas activas) en Colombia, México, Argentina, Chile y Perú. Sin auto-promoción: solo data.',
    ],
    sections: [
      {
        heading: 'Top hard skills transversales',
        body: [
          'Estas son las skills que aparecen en más del 18% de las ofertas, sin importar el sector. Son las que más vale la pena tener en el CV, aunque tu rol específico no sea técnico.',
        ],
        bullets: [
          'Excel avanzado — 31% de las ofertas. No solo finanzas: marketing, operaciones, RRHH.',
          'Inglés intermedio o superior — 27%. Sube a 65% en roles tech/remote.',
          'Manejo de CRM (HubSpot, Salesforce o similar) — 19%. Mucho más allá de ventas.',
          'Análisis de datos básico (interpretar dashboards, Google Analytics) — 18%.',
          'Comunicación escrita clara (mencionada explícitamente) — 18%.',
        ],
      },
      {
        heading: 'Top skills por sector',
        body: [
          'Si filtramos por industria, el panorama se especializa. Estas son las 3 más demandadas por vertical:',
        ],
        bullets: [
          'Tech: TypeScript, AWS, Python — en ese orden, juntas en el 70% de las ofertas dev.',
          'Marketing digital: Google Ads, Meta Ads, SEO — el trío sigue dominando, sin grandes movimientos.',
          'Finanzas: NIIF, SAP, modelado financiero. NIIF subió fuerte por la convergencia regional con IFRS.',
          'Ventas B2B: Salesforce, prospección, KPIs. Pipeline management aparece cada vez más como requisito explícito.',
          'Operaciones / supply chain: Lean, ERP (SAP MM/PP/WM), Six Sigma.',
          'RRHH / People Ops: ATS (Greenhouse, Workday), people analytics, employer branding.',
        ],
      },
      {
        heading: 'Lo que está subiendo',
        body: [
          'Comparando los últimos 90 días contra los 90 anteriores, estas son las skills que crecieron más en demanda:',
        ],
        bullets: [
          '"Prompt engineering" y manejo de IA generativa: aparece en 12% de las ofertas, contra 3% hace 6 meses.',
          'Customer success / retention: el shift de growth-at-all-costs a unit economics está creando demanda fuerte.',
          'Sostenibilidad / ESG: presente sobre todo en empresas grandes con compromisos ambientales.',
          'Habilidades de facilitación y workshops async: el work-from-anywhere maduró y requiere nuevas competencias.',
        ],
        callout:
          'Si te toca elegir UNA skill para aprender este trimestre, manejo aplicado de IA generativa es la apuesta con más upside.',
      },
      {
        heading: 'Lo que está bajando',
        body: [
          'Algunas skills que parecían imprescindibles están perdiendo peso:',
        ],
        bullets: [
          'jQuery: cayó al 4% en ofertas frontend. React/Vue dominaron el reemplazo.',
          'Manejo "experto" de Microsoft Office: bajó porque ahora se asume.',
          'Photoshop "experto" en marketing: Figma + Canva cubren la necesidad real en muchos casos.',
        ],
      },
      {
        heading: 'Cómo usar este reporte',
        body: [
          'No optimices tu CV para tener TODAS las skills. Eso luce sospechoso. Optimízalo para tener las que de verdad usaste, expresadas con las palabras que el mercado usa hoy.',
          'Si estás en transición de carrera, usa estos datos para priorizar qué aprender primero — el ROI de tu tiempo es más alto si apuntas a skills con demanda alta y oferta limitada.',
        ],
      },
    ],
    closing: [
      'Este reporte se actualiza cada trimestre. Si quieres que llegue a tu correo, créate cuenta — los suscriptores reciben la versión expandida con breakdown por país y rango salarial estimado.',
    ],
  },

  // ============================================================
  // Entrevistas remotas
  // ============================================================
  {
    slug: 'entrevistas-remotas',
    category: 'Guía',
    readMinutes: 12,
    title: 'Preparación para entrevistas remotas (cualquier rol)',
    excerpt:
      'Setup, cámara, performance bajo presión y cómo manejar al entrevistador difícil. Aplica a cualquier profesión.',
    intro: [
      'La entrevista por videollamada es el formato estándar hoy. Lo que hace 10 años era una conversación en persona ahora es un Zoom de 45 minutos, y las reglas del juego son distintas. La mayoría de los problemas no son sobre tu experiencia o tus respuestas — son técnicos, de presentación, o de manejo del tiempo.',
      'Esta guía aplica a cualquier rol: comercial, técnico, gerencial, creativo. La diferencia entre una entrevista buena y una mediocre suele estar en los detalles que casi nadie prepara.',
    ],
    sections: [
      {
        heading: 'Setup técnico: lo que no se ve, importa',
        body: [
          'El primer minuto de la entrevista lo defines tú. Si llegas con cámara borrosa, audio con eco y conexión inestable, el entrevistador ya tiene una impresión negativa antes de que abras la boca. Estas son las reglas no negociables:',
        ],
        bullets: [
          'Cámara: si tu laptop tiene una decente, úsala. Si tu laptop es de 2018 y la cámara se ve mal, invierte en una externa básica de US$30. Vale el upgrade.',
          'Iluminación: la luz va al frente, nunca atrás. Una ventana detrás de ti te convierte en silueta. Si no tienes opción, prende todas las luces del cuarto.',
          'Audio: usa audífonos con micrófono. El micrófono interno de la laptop captura el eco del cuarto y todos los ruidos del entorno.',
          'Conexión: si es posible, conecta por Ethernet. Si vas por WiFi, siéntate cerca del router. Test rápido: pruébalo con un amigo 30 min antes de la real.',
          'Fondo: limpio y neutral. Si no tienes espacio, usa el blur de Zoom/Teams — no fondos virtuales con palmeras, distraen.',
        ],
      },
      {
        heading: 'El pitch de 60 segundos',
        body: [
          '"Cuéntame de ti" es la pregunta más común y la peor respondida. La mayoría improvisa, divaga, y arruina el primer momento. Prepáralo escrito, ensáyalo en voz alta al menos 3 veces.',
          'La estructura que funciona:',
        ],
        bullets: [
          '15s — Quién eres profesionalmente HOY (rol, sector, años de experiencia).',
          '20s — Un logro concreto que demuestre tu valor (con número si es posible).',
          '15s — Por qué este puesto te interesa específicamente.',
          '10s — Cierre/pivote: "Me gustaría contarte más sobre [tema específico del JD]".',
        ],
        callout:
          'El pitch de 60s no es para impresionar. Es para no perder el control del primer minuto.',
      },
      {
        heading: 'La pregunta más subestimada: la tuya',
        body: [
          'Al final de cada entrevista te van a preguntar "¿tienes preguntas?". La respuesta correcta NUNCA es "no, está claro". Eso comunica desinterés, falta de preparación, o que solo querías la entrevista por probar.',
          'Lleva 3 preguntas mínimo, y haz al menos 2. Sobre estos temas:',
        ],
        bullets: [
          'El equipo: "¿Cómo está estructurado el equipo del que sería parte? ¿Quién es mi manager directo?".',
          'El éxito en el rol: "¿Cómo se vería un primer 90 días exitoso en esta posición?".',
          'El proceso: "¿Cuáles son los próximos pasos del proceso? ¿Cuántas etapas más?".',
        ],
      },
      {
        heading: 'Cuando no sabes la respuesta',
        body: [
          'Te van a preguntar algo que no sepas. Pasa siempre. La diferencia entre quien gana la entrevista y quien la pierde no es saber todo — es manejar el "no sé" con elegancia.',
          'Lo que NO funciona: inventar, divagar, intentar redirigir a algo que sí sabes. El entrevistador lo nota inmediatamente.',
          'Lo que sí funciona: "No tengo experiencia directa con eso. Lo que sí sé es [conocimiento adyacente]. Si tuviera que aprenderlo, mi primer paso sería [aproximación concreta]". Demuestra autoconciencia y capacidad de aprendizaje — dos rasgos muy buscados en cualquier rol.',
        ],
      },
      {
        heading: 'Entrevistador difícil: cómo no perder los nervios',
        body: [
          'A veces te toca alguien hostil: te interrumpe, cuestiona cada respuesta, pone cara de aburrimiento. No es personal — algunos entrevistadores usan presión deliberadamente para ver cómo reaccionas, otros simplemente son malos comunicadores.',
          'Tu única tarea es no entrar al juego. Respira antes de responder. Da respuestas más cortas, más concretas, más calmas. Si una pregunta es agresiva, pide aclaración: "¿Me podrías reformular la pregunta?" — eso desacelera el ritmo y te da tiempo de pensar.',
          'Si después de la entrevista te sentiste maltratado de verdad, esa empresa no te merece. Es información válida para tomar tu decisión final.',
        ],
      },
      {
        heading: 'Después de la entrevista',
        body: [
          'Mandar un correo de seguimiento dentro de las 24h te diferencia del 80% que no lo hace. No tiene que ser largo:',
        ],
        bullets: [
          'Agradece el tiempo y la conversación.',
          'Menciona UN punto específico de lo que hablaron — demuestra que escuchaste.',
          'Reafirma tu interés en seguir adelante.',
          'No más de 4 líneas. Más es spam.',
        ],
      },
    ],
    closing: [
      'La preparación de una entrevista buena toma 2 horas, no 20. Lo importante no es saber todo el contexto de la empresa — es tener tu pitch listo, tus preguntas armadas, y tu setup técnico funcionando. Eso te ubica arriba del 80% de los candidatos.',
      'Si llegaste hasta acá, ya estás mejor preparado que la mayoría. Suerte en la próxima.',
    ],
  },
];

export function findArticleBySlug(slug: string): Article | undefined {
  return ARTICLES.find((a) => a.slug === slug);
}
