/**
 * Mirror del classifier de profesión del backend
 * (`backend/users/services/profession_classifier.py`).
 *
 * Lo mantenemos duplicado y NO via API porque el cliente lo necesita
 * para armar el query param del endpoint `/api/tips/today/` ANTES del
 * primer request: bajar la profession requeriría primero pegarle a
 * `/me` y después a `/tips/today/`, dos roundtrips para el tip del
 * sidebar. Mejor calcular client-side desde el `professional_title`
 * que ya tenemos en localStorage/sessionStorage.
 *
 * Si los patrones de un lado se actualizan, hay que reflejarlo del
 * otro. La cobertura no necesita ser idéntica al 100% — si el frontend
 * detecta 'general' donde el backend hubiera dicho 'sales', el endpoint
 * devuelve tips universales (que el usuario igual entiende). Pequeño
 * trade-off por la simplicidad de no centralizar.
 */

export type ProfessionCategory =
  | 'tech'
  | 'design'
  | 'marketing'
  | 'sales'
  | 'finance'
  | 'hr'
  | 'operations'
  | 'health'
  | 'education'
  | 'legal'
  | 'general';

/** Tupla (categoría, regex) — el primer match gana, orden importa. */
const _PATTERNS: ReadonlyArray<readonly [ProfessionCategory, RegExp]> = [
  [
    'tech',
    /\b(developer|engineer|programmer|programador|desarrollador|devops|sysadmin|sre|qa|tester|architect|arquitecto|fullstack|frontend|backend|mobile|ios|android|data scientist|data engineer|data analyst|machine learning|ml engineer|product owner|technical lead|tech lead|cto|cio)\b/i,
  ],
  [
    'design',
    /\b(diseñador|disenador|designer|ux|ui|ux\/ui|product designer|graphic designer|motion designer|illustrator|ilustrador|industrial designer|director de arte|art director)\b/i,
  ],
  [
    'marketing',
    /\b(marketing|marketer|seo|sem|community manager|content|copywriter|growth|brand|digital strategist|social media|publicidad|advertising|performance)\b/i,
  ],
  [
    'sales',
    /\b(ventas|vendedor|comercial|sales|account executive|account manager|business development|sdr|bdr|key account|customer success|kam|representante comercial)\b/i,
  ],
  [
    'finance',
    /\b(contador|contadora|accountant|cfo|finance|finanzas|financial|auditor|auditoría|auditoria|tesorero|controller|analista financiero|treasury|fp&a|impuestos|tax)\b/i,
  ],
  [
    'hr',
    /\b(rrhh|recursos humanos|hr|human resources|reclutador|reclutadora|recruiter|talent|talent acquisition|people|payroll|nominas|chro|gente y cultura)\b/i,
  ],
  [
    'operations',
    /\b(operations|operaciones|supply chain|cadena de suministro|logística|logistica|warehouse|almacén|almacen|production manager|jefe de producción|jefe de produccion|coo|director de operaciones|planning|planificación|planificacion)\b/i,
  ],
  [
    'health',
    /\b(médico|medico|doctor|enfermero|enfermera|nurse|odontólogo|odontologo|psicólogo|psicologo|fisioterapeuta|nutricionista|farmacéutico|farmaceutico|bioanalista|radiólogo|radiologo|terapeuta)\b/i,
  ],
  [
    'education',
    /\b(docente|profesor|profesora|teacher|maestra|maestro|educador|educadora|tutor|coordinador académico|coordinador academico|rector|director académico|director academico)\b/i,
  ],
  [
    'legal',
    /\b(abogado|abogada|lawyer|jurídico|juridico|legal counsel|paralegal|notario|notaria|compliance officer|jurista)\b/i,
  ],
];

export function inferProfessionCategory(title: string | null | undefined): ProfessionCategory {
  if (!title) return 'general';
  for (const [category, pattern] of _PATTERNS) {
    if (pattern.test(title)) {
      return category;
    }
  }
  return 'general';
}
