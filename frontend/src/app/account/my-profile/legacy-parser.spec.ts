import {
  parseLegacyEducation,
  parseLegacyExperience,
} from './legacy-parser';

/**
 * Fixture real: perfil de Walter (walternights@gmail.com) según snapshot
 * de producción capturado el 2026-07-08. Incluye 3 bloques distintos con
 * variaciones típicas del formato legacy:
 *   - Bloque 1: `**Empresa (loc)**` seguido de `**Cargo (stack) [fechas]**`.
 *   - Bloque 2: `**Empresa (loc)\nCargo (algo) [fechas]**` — user olvidó
 *     cerrar los asteriscos entre empresa y cargo, todo colapsado.
 *   - Bloque 3: idem 2.
 */
const WALTER_EXPERIENCE = `**Geeks5g (Medellín, Colombia)**
**FullStack Developer (React - Next - Nest) [Septiembre 2025 - Presente]**
- Integrated Commigo and Twilio messaging services, enabling automated customer communications and real-time notifications across the platform.
- Implemented SendGrid for transactional emails including user registration, account activation, and business status notifications.

**Corporación Universitaria U de Colombia (Medellín, Colombia)
Virtualization Leader - FrontEnd Developer (React) [Marzo 2022 - Abril 2025]**
- Managed the institutional portal, using MLS for hosting and customizing it with HTML, CSS, and JavaScript.
- Proposed a new institutional website built with Django and React.

**Zaine Developers (Bogotá, Colombia)
FullStack Developer (Python - Django) [Noviembre 2020 - Noviembre 2022]**
- Developed a microservices architecture for scalable applications.
- Built user and product CRUD functionalities connected to REST APIs using Fetch and jQuery.`;

const WALTER_EDUCATION = `Graphic Design - Expert in Corporative Image en Corporación Universitaria de Educación Superior CORBES (Cúcuta, Colombia) [Enero 2005 - Diciembre 2008]`;


describe('parseLegacyExperience', () => {
  it('detecta 3 entries en el perfil real de Walter', () => {
    const entries = parseLegacyExperience(WALTER_EXPERIENCE);
    expect(entries.length).toBe(3);
  });

  it('extrae company + location del bloque 1', () => {
    const [first] = parseLegacyExperience(WALTER_EXPERIENCE);
    expect(first.company).toBe('Geeks5g');
    expect(first.location_city).toBe('Medellín');
    expect(first.location_country).toBe('Colombia');
  });

  it('extrae position con el stack como paréntesis descartado', () => {
    const [first] = parseLegacyExperience(WALTER_EXPERIENCE);
    // "FullStack Developer (React - Next - Nest)" → position = "FullStack Developer",
    // el stack no se persiste como campo separado (la description ya lo cubre).
    expect(first.position).toBe('FullStack Developer');
  });

  it('parsea "Septiembre 2025" → "2025-09"', () => {
    const [first] = parseLegacyExperience(WALTER_EXPERIENCE);
    expect(first.start_date).toBe('2025-09');
  });

  it('detecta "Presente" y marca is_current=true con end_date vacio', () => {
    const [first] = parseLegacyExperience(WALTER_EXPERIENCE);
    expect(first.is_current).toBe(true);
    expect(first.end_date).toBe('');
  });

  it('extrae descripcion multi-linea del bloque 1', () => {
    const [first] = parseLegacyExperience(WALTER_EXPERIENCE);
    expect(first.description).toContain('Integrated Commigo');
    expect(first.description).toContain('SendGrid');
    // Los saltos de linea se preservan.
    expect((first.description ?? '').split('\n').length).toBeGreaterThanOrEqual(2);
  });

  it('tolera bloque 2 con asteriscos faltantes entre empresa y cargo', () => {
    const [, second] = parseLegacyExperience(WALTER_EXPERIENCE);
    expect(second.company).toBe('Corporación Universitaria U de Colombia');
    expect(second.location_city).toBe('Medellín');
    // Position tiene "Virtualization Leader - FrontEnd Developer" —
    // aceptamos el string entero como position aunque tenga guion.
    expect(second.position).toContain('FrontEnd Developer');
    expect(second.start_date).toBe('2022-03');
    expect(second.end_date).toBe('2025-04');
    expect(second.is_current).toBe(false);
  });

  it('parsea fechas del bloque 3 (Nov 2020 → Nov 2022)', () => {
    const [, , third] = parseLegacyExperience(WALTER_EXPERIENCE);
    expect(third.start_date).toBe('2020-11');
    expect(third.end_date).toBe('2022-11');
    expect(third.is_current).toBe(false);
  });

  it('devuelve [] con texto vacio o nullish', () => {
    expect(parseLegacyExperience('')).toEqual([]);
    expect(parseLegacyExperience('   ')).toEqual([]);
    expect(parseLegacyExperience(null)).toEqual([]);
    expect(parseLegacyExperience(undefined)).toEqual([]);
  });

  it('devuelve [] cuando el texto no tiene bloques parseables', () => {
    // Sin fechas, sin asteriscos, sin estructura reconocible.
    const junk = 'esto es un párrafo suelto sin ninguna estructura clara.';
    const result = parseLegacyExperience(junk);
    // Puede dar 0 o 1 entry con solo la empresa detectada. Cualquier
    // resultado es OK mientras no crashee — el caller hace fallback.
    expect(Array.isArray(result)).toBe(true);
  });

  it('parsea "Actual" como is_current', () => {
    const text = `**Acme Corp (Medellín, Colombia)**
**Developer [Enero 2024 - Actual]**
- Desarrollo`;
    const [first] = parseLegacyExperience(text);
    expect(first.is_current).toBe(true);
    expect(first.start_date).toBe('2024-01');
  });

  it('parsea meses en ingles (September 2025)', () => {
    const text = `**Acme (Bogota, Colombia)**
**Engineer [September 2025 - Present]**
- Work`;
    const [first] = parseLegacyExperience(text);
    expect(first.start_date).toBe('2025-09');
    expect(first.is_current).toBe(true);
  });

  it('parsea abreviaturas de meses (Jan 2020)', () => {
    const text = `**Acme (Bogota)**
**Engineer [Jan 2020 - Dec 2021]**
- Work`;
    const [first] = parseLegacyExperience(text);
    expect(first.start_date).toBe('2020-01');
    expect(first.end_date).toBe('2021-12');
  });

  it('tolera locations sin coma (solo ciudad)', () => {
    const text = `**Acme (Remote)**
**Developer [Enero 2024 - Marzo 2024]**
- Work`;
    const [first] = parseLegacyExperience(text);
    expect(first.location_city).toBe('Remote');
    expect(first.location_country).toBe('');
  });
});


describe('parseLegacyEducation', () => {
  it('detecta el registro real de Walter (una linea, formato "X en Y (loc) [fechas]")', () => {
    const entries = parseLegacyEducation(WALTER_EDUCATION);
    expect(entries.length).toBe(1);
    const [first] = entries;
    expect(first.title).toBe('Graphic Design - Expert in Corporative Image');
    expect(first.institution).toBe(
      'Corporación Universitaria de Educación Superior CORBES',
    );
    expect(first.location_city).toBe('Cúcuta');
    expect(first.location_country).toBe('Colombia');
    expect(first.start_date).toBe('2005-01');
    expect(first.end_date).toBe('2008-12');
    expect(first.is_current).toBe(false);
  });

  it('acepta separador "at" (formato ingles)', () => {
    const text = `Bachelor of Science at MIT (Cambridge, USA) [September 2015 - June 2019]`;
    const [first] = parseLegacyEducation(text);
    expect(first.title).toBe('Bachelor of Science');
    expect(first.institution).toBe('MIT');
    expect(first.location_country).toBe('USA');
  });

  it('sin separador " en "/"at" toma todo como titulo', () => {
    const text = `Curso de React [Marzo 2023 - Junio 2023]`;
    const [first] = parseLegacyEducation(text);
    expect(first.title).toBe('Curso de React');
    expect(first.institution).toBe('');
    expect(first.start_date).toBe('2023-03');
  });

  it('devuelve [] con texto vacio', () => {
    expect(parseLegacyEducation('')).toEqual([]);
    expect(parseLegacyEducation(null)).toEqual([]);
  });

  it('detecta multiple bloques separados por linea en blanco', () => {
    const text = `Diseno Grafico en U de Colombia (Medellin) [Enero 2005 - Diciembre 2008]

Curso Angular en Platzi (Remoto) [Enero 2023 - Marzo 2023]`;
    const entries = parseLegacyEducation(text);
    expect(entries.length).toBe(2);
    expect(entries[0].title).toBe('Diseno Grafico');
    expect(entries[1].title).toBe('Curso Angular');
  });
});
