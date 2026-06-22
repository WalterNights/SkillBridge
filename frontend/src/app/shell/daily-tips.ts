/**
 * Tips estáticos para el widget "Tip del día" del sidebar del AppShell.
 *
 * Rotación: deterministic por day-of-year — el mismo tip todo el día,
 * cambia a medianoche del browser. Con 50 tips, el ciclo se repite cada
 * ~7 semanas — suficiente para que se sienta fresco para usuarios
 * diarios sin tocar backend.
 *
 * Cuando los tips empiecen a repetirse, Fase 2 del plan: modelo Tip en
 * DB + tarea semanal de Gemini que agrega 5-7 entradas nuevas.
 *
 * Reglas de estilo:
 *   - Una idea por tip. Si necesita "y además", partirlo en dos.
 *   - Tono accionable: empieza con verbo en imperativo (Personalizá,
 *     Sumá, Pegale, Pedí, Guardá).
 *   - Entre 80 y 160 chars — más largo desborda el card.
 *   - Sin emojis ni markdown, el widget renderiza texto plano.
 *   - Voseo argentino para consistencia con el resto del producto.
 */
export const DAILY_TIPS: readonly string[] = [
  // ----- CV / ATS optimization -----
  'Personalizá el resumen del CV para cada match. La IA detecta keywords del job post.',
  'Usá los mismos términos que la oferta: si pide "JavaScript", no escribas "JS".',
  'Eliminá tablas e imágenes del CV — los ATS no las leen y descartan el resto.',
  'Tu CV ideal tiene 1-2 páginas. Si tenés más de 7 años de experiencia, dos. Si menos, una.',
  'Empezá cada bullet con un verbo de acción: lideré, implementé, optimicé, reduje.',
  'Acompañá los logros con números: "Reduje el tiempo de carga 40%" pega más que "mejoré performance".',
  'El "Sobre mí" del CV no es una bio — son 3 líneas sobre qué buscás y qué traés.',
  'Guardá el CV como PDF, nunca como .docx. El formato se rompe entre versiones de Word.',

  // ----- Búsqueda activa -----
  'Postulá a 10 ofertas con CV personalizado antes que a 50 con el mismo PDF.',
  'Activá las alertas: ver una oferta el día que sale tiene 3x más respuesta que verla a la semana.',
  'Investigá la empresa antes de aplicar. Si no sabés qué hacen, el reclutador lo nota en 30 segundos.',
  'No filtres por salario si el rango no aparece. Mejor preguntar en la primera llamada.',
  'Las ofertas de viernes tarde suelen tener menos competencia el lunes a la mañana.',
  'Si una oferta lleva más de 30 días publicada, ya bajó la prioridad del HR. No te ilusiones.',
  'Mirá si la empresa renueva la misma oferta cada mes — puede indicar rotación alta del rol.',

  // ----- Entrevistas -----
  'Practicá tu pitch de 60 segundos antes de cualquier entrevista. Lo van a pedir.',
  'Llegá 5 minutos antes a una entrevista virtual. No 15, no 0. Cinco.',
  'La pregunta "¿tenés preguntas?" es la mitad de la entrevista. Llevá 3 preparadas.',
  'Preguntá por el equipo, no solo por el rol. Vas a trabajar con personas, no con un job description.',
  'Si no sabés algo en una técnica, decilo. "No lo sé pero así lo investigaría" pega mejor que inventar.',
  'Repasá tu CV antes de la entrevista. Si no podés explicar algo que está ahí, sacalo.',
  'Después de una entrevista, mandá un mail corto agradeciendo el tiempo. Cuesta 2 min, pesa más de lo que parece.',

  // ----- Networking / marca personal -----
  'Un LinkedIn con foto y headline claro recibe 14x más visitas que uno sin foto.',
  'Pediles a 3 colegas que te escriban una recommendation en LinkedIn. La conversion en mensajes sube notable.',
  'Tu URL de LinkedIn debería ser tu nombre. /walternights vs /walter-juan-perez-12345 — cambia mucho.',
  'Comentar 1 post por día en tu industria te hace más visible que postear 1 vez por semana.',
  'No conectes con "Hola, vi tu perfil". Mencioná algo específico — un proyecto, un post, un proyecto en común.',
  'Mostrá lo que estás aprendiendo, no solo lo que ya sabés. Recruiters le siguen a quien crece.',

  // ----- Soft skills / negociación -----
  'No menciones tu sueldo actual hasta que te pregunten 2 veces. La primera oferta sale del rango que vos pidas.',
  'Si te ofrecen un rango, pedí el techo + 10%. Es estándar y muestra que sabés negociar.',
  'Antes de aceptar, pedí 24h para "revisar el paquete completo". Te respetan más por la pausa.',
  'Beneficios > sueldo bruto si tenés flexibilidad. Home office, días extra y health insurance suman miles al año.',
  'Si el proceso es lento (>4 semanas sin avance), tomalo como señal. Así trabajan internamente.',

  // ----- Técnicas / industry-specific -----
  'GitHub vacío es worse que GitHub con commits viejos. Pegale al menos 1 commit por mes a algo público.',
  'Un README bien escrito en tu repo más visible pesa más que 10 repos sin descripción.',
  'Si te piden "experiencia con X" y trabajaste un mes con X, decí "experiencia". No esperes 2 años.',
  'Stack overflow profile, blog técnico o repos con stars pesan en técnicas. Mostralos en el CV.',
  'Postulate a roles que pidan 70% de lo que sabés. El 30% restante se aprende y te pagan por aprenderlo.',
  'Si la oferta lista 15 tecnologías, el 30% son "nice to have". No te autocenseures por no saber todas.',

  // ----- SkilTak meta-tips (uso del producto) -----
  'Subí un CV completo a SkilTak. La IA matchea mejor con seniority, stack y location reales.',
  'Refrescá las ofertas cada 2-3 días. Los nuevos posts de LinkedIn entran rápido al feed.',
  'Mirá los "Skills faltantes" del job-detail. Te dicen exactamente qué cerrar antes de aplicar a esa empresa.',
  'Guardá las ofertas con +80% match aunque no apliques ya. Sirven para benchmark del mercado.',
  'Si todos tus matches están abajo del 50%, ajustá el "Título profesional" del perfil. Es el mayor peso.',
  'Marcá leídas las notificaciones que ya viste para no perder track de las nuevas.',

  // ----- Diversificación / wellness -----
  'No apliques en pánico un viernes a las 11 de la noche. El lunes con calma vas a postular mejor.',
  'Tomate medio día libre al cierre de cada sprint de búsqueda. La fatiga te baja el filtro de calidad.',
  'Llevá una hoja con las empresas a las que aplicaste: nombre, fecha, contacto, estado. Saber el embudo te calma.',
  'Tener una entrevista por semana es saludable. Más, es estrés. Menos, falta de pipeline.',
  'Si rechazaron tu aplicación, pedí feedback breve. 1 de cada 3 te responde algo útil.',
  'No tomes los rechazos como referendum. La mayoría son timing, presupuesto, o un perfil que ya tenían.',
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
 * abierta cruzando medianoche (caso borde, no vale el complejidad).
 */
export function getTipOfTheDay(): string {
  return DAILY_TIPS[dayOfYear() % DAILY_TIPS.length];
}
