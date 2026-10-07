import { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';

export const PASSWORD_MIN_LENGTH = 8;

/** Una regla de contraseña, con el texto que ve el usuario. */
export interface PasswordRule {
  id: 'length' | 'letter' | 'number' | 'symbol';
  label: string;
  test: (password: string) => boolean;
}

/**
 * Reglas del registro. "Símbolo" es CUALQUIER carácter que no sea letra,
 * número ni espacio: antes solo valían `!@#$%^&*()_+{}:"<>?` y contraseñas
 * como "buenas.1234" o "Clave-2024" se rechazaban sin explicar por qué.
 * Letras con tilde y ñ cuentan como letras, no como símbolos.
 */
export const PASSWORD_RULES: readonly PasswordRule[] = [
  {
    id: 'length',
    label: `Al menos ${PASSWORD_MIN_LENGTH} caracteres`,
    test: (p) => p.length >= PASSWORD_MIN_LENGTH,
  },
  { id: 'letter', label: 'Al menos una letra', test: (p) => /\p{L}/u.test(p) },
  { id: 'number', label: 'Al menos un número', test: (p) => /\d/.test(p) },
  {
    id: 'symbol',
    label: 'Al menos un símbolo (. - _ ! @ # …)',
    test: (p) => /[^\p{L}\d\s]/u.test(p),
  },
];

/** Estado de cada regla para la contraseña actual (para la lista en vivo). */
export function checkPasswordRules(password: string): { rule: PasswordRule; ok: boolean }[] {
  return PASSWORD_RULES.map((rule) => ({ rule, ok: rule.test(password ?? '') }));
}

/** Validator de Angular: `{ passwordRules: ['symbol', …] }` con las que faltan. */
export const strongPasswordValidator: ValidatorFn = (
  control: AbstractControl,
): ValidationErrors | null => {
  const value: string = control.value ?? '';
  if (!value) return null; // `Validators.required` reporta el vacío
  const failed = PASSWORD_RULES.filter((rule) => !rule.test(value)).map((rule) => rule.id);
  return failed.length ? { passwordRules: failed } : null;
};

/**
 * Misma regla que el `UnicodeUsernameValidator` de Django: letras (con tilde
 * o ñ), números y `@ . + - _`, sin espacios. Validarla acá evita que el
 * usuario descubra el problema recién al enviar ("Pepe Perez").
 */
export const USERNAME_PATTERN = /^[\p{L}\p{N}_.@+-]+$/u;
export const USERNAME_MAX_LENGTH = 150;
export const USERNAME_FORMAT_HINT = 'Solo letras, números y los símbolos @ . + - _ (sin espacios).';
