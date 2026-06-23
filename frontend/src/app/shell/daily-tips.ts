/**
 * Tips estáticos para el widget "Tip del día" del sidebar del AppShell.
 *
 * Rotación: determinística por day-of-year — el mismo tip todo el día,
 * cambia a medianoche del browser. Con 51 tips, el ciclo se repite cada
 * ~7 semanas — suficiente para que se sienta fresco para usuarios
 * diarios sin tocar backend.
 *
 * Cuando los tips empiecen a repetirse, fase 2 del plan: modelo Tip en
 * DB + tarea semanal de Gemini que agrega 5-7 entradas nuevas.
 *
 * Reglas de estilo:
 *   - Una idea por tip. Si necesita "y además", partirlo en dos.
 *   - Tono accionable: verbo en imperativo estándar (Personaliza, Usa,
 *     Pide, Guarda). Sin voseo — el producto apunta a toda Latam.
 *   - Entre 80 y 160 chars — más largo desborda el card.
 *   - Sin emojis ni markdown, el widget renderiza texto plano.
 *   - Español neutro: "tú/tu" en vez de "vos/tuyo argentino".
 */
export const DAILY_TIPS: readonly string[] = [
  // ----- CV / ATS optimization -----
  'Personaliza el resumen del CV para cada match. La IA detecta keywords del job post.',
  'Usa los mismos términos que la oferta: si pide "JavaScript", no escribas "JS".',
  'Elimina tablas e imágenes del CV — los ATS no las leen y descartan el resto.',
  'Tu CV ideal tiene 1-2 páginas. Si tienes más de 7 años de experiencia, dos. Si menos, una.',
  'Empieza cada bullet con un verbo de acción: lideré, implementé, optimicé, reduje.',
  'Acompaña los logros con números: "Reduje el tiempo de carga 40%" pega más que "mejoré performance".',
  'El "Sobre mí" del CV no es una bio — son 3 líneas sobre qué buscas y qué traes.',
  'Guarda el CV como PDF, nunca como .docx. El formato se rompe entre versiones de Word.',

  // ----- Búsqueda activa -----
  'Postúlate a 10 ofertas con CV personalizado antes que a 50 con el mismo PDF.',
  'Activa las alertas: ver una oferta el día que sale tiene 3x más respuesta que verla a la semana.',
  'Investiga la empresa antes de aplicar. Si no sabes qué hacen, el reclutador lo nota en 30 segundos.',
  'No filtres por salario si el rango no aparece. Mejor preguntar en la primera llamada.',
  'Las ofertas de viernes en la tarde suelen tener menos competencia el lunes en la mañana.',
  'Si una oferta lleva más de 30 días publicada, ya bajó la prioridad del HR. No te ilusiones.',
  'Mira si la empresa renueva la misma oferta cada mes — puede indicar rotación alta del rol.',

  // ----- Entrevistas -----
  'Practica tu pitch de 60 segundos antes de cualquier entrevista. Lo van a pedir.',
  'Llega 5 minutos antes a una entrevista virtual. No 15, no 0. Cinco.',
  'La pregunta "¿tienes preguntas?" es la mitad de la entrevista. Lleva 3 preparadas.',
  'Pregunta por el equipo, no solo por el rol. Vas a trabajar con personas, no con un job description.',
  'Si no sabes algo técnico, dilo. "No lo sé pero así lo investigaría" pega mejor que inventar.',
  'Repasa tu CV antes de la entrevista. Si no puedes explicar algo que está ahí, sácalo.',
  'Después de una entrevista, manda un correo corto agradeciendo el tiempo. Cuesta 2 min, pesa más de lo que parece.',

  // ----- Networking / marca personal -----
  'Un LinkedIn con foto y headline claro recibe 14x más visitas que uno sin foto.',
  'Pide a 3 colegas que te escriban una recommendation en LinkedIn. La conversión en mensajes sube notable.',
  'Tu URL de LinkedIn debería ser tu nombre. /walternights vs /walter-juan-perez-12345 — cambia mucho.',
  'Comentar 1 post por día en tu industria te hace más visible que postear 1 vez por semana.',
  'No conectes con "Hola, vi tu perfil". Menciona algo específico — un proyecto, un post, un interés en común.',
  'Muestra lo que estás aprendiendo, no solo lo que ya sabes. Recruiters siguen a quien crece.',

  // ----- Soft skills / negociación -----
  'No menciones tu sueldo actual hasta que te pregunten 2 veces. La primera oferta sale del rango que tú pidas.',
  'Si te ofrecen un rango, pide el techo + 10%. Es estándar y muestra que sabes negociar.',
  'Antes de aceptar, pide 24h para "revisar el paquete completo". Te respetan más por la pausa.',
  'Beneficios > sueldo bruto si tienes flexibilidad. Home office, días extra y seguro médico suman miles al año.',
  'Si el proceso es lento (>4 semanas sin avance), tómalo como señal. Así trabajan internamente.',

  // ----- Técnicas / industry-specific -----
  'GitHub vacío es peor que GitHub con commits viejos. Haz al menos 1 commit por mes a algo público.',
  'Un README bien escrito en tu repo más visible pesa más que 10 repos sin descripción.',
  'Si piden "experiencia con X" y trabajaste un mes con X, escribe "experiencia". No esperes 2 años.',
  'Stack overflow profile, blog técnico o repos con stars pesan en técnicas. Muéstralos en el CV.',
  'Postúlate a roles que pidan 70% de lo que sabes. El 30% restante se aprende y te pagan por aprenderlo.',
  'Si la oferta lista 15 tecnologías, el 30% son "nice to have". No te autocensures por no saber todas.',

  // ----- SkilTak meta-tips (uso del producto) -----
  'Sube un CV completo a SkilTak. La IA hace mejor match con seniority, stack y ubicación reales.',
  'Refresca las ofertas cada 2-3 días. Los nuevos posts de LinkedIn entran rápido al feed.',
  'Mira los "Skills faltantes" del job-detail. Te dicen exactamente qué cerrar antes de aplicar a esa empresa.',
  'Guarda las ofertas con +80% match aunque no apliques ya. Sirven para benchmark del mercado.',
  'Si todos tus matches están por debajo del 50%, ajusta el "Título profesional" del perfil. Es el mayor peso.',
  'Marca como leídas las notificaciones que ya viste para no perder track de las nuevas.',

  // ----- Diversificación / wellness -----
  'No apliques en pánico un viernes a las 11 de la noche. El lunes con calma vas a postular mejor.',
  'Tómate medio día libre al cierre de cada sprint de búsqueda. La fatiga te baja el filtro de calidad.',
  'Lleva una hoja con las empresas a las que aplicaste: nombre, fecha, contacto, estado. Saber el embudo te calma.',
  'Tener una entrevista por semana es saludable. Más, es estrés. Menos, falta de pipeline.',
  'Si rechazaron tu aplicación, pide feedback breve. 1 de cada 3 te responde algo útil.',
  'No tomes los rechazos como referéndum. La mayoría son timing, presupuesto, o un perfil que ya tenían.',
];


/**
 * Devuelve el día del año (1-366) para una fecha dada. Usado para
 * rotar el tip de forma determinística — mismo tip todo el día, cambia
 * a medianoche.
 */
function dayOfYear(d: Date = new Date()): number {
  const start = new Date(d.getFullYear(), 0, 0);
  const diff = d.getTime() - start.getTime();
  return Math.floor(diff / (1000 * 60 * 60 * 24));
}

/**
 * El tip de hoy. Pure function — el componente lo computa una vez al
 * montarse, no hay que invalidar nada salvo si el user deja la pestaña
 * abierta cruzando medianoche (caso borde, no vale la complejidad).
 */
export function getTipOfTheDay(): string {
  return DAILY_TIPS[dayOfYear() % DAILY_TIPS.length];
}
