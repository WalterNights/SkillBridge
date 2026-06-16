/**
 * Genera `src/environment/environment.prod.ts` leyendo el `.env` del root.
 * Se ejecuta antes de `ng build` (ver script `prebuild` en package.json).
 *
 * Variables consumidas:
 *   - FRONTEND_API_URL
 *
 * El archivo generado está gitignored.
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const ENV_FILE = path.join(ROOT, '.env');
const OUT_FILE = path.join(__dirname, '..', 'src', 'environment', 'environment.prod.ts');

function parseEnv(content) {
  const out = {};
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const eq = line.indexOf('=');
    if (eq === -1) continue;
    const key = line.slice(0, eq).trim();
    let value = line.slice(eq + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    out[key] = value;
  }
  return out;
}

const env = fs.existsSync(ENV_FILE)
  ? parseEnv(fs.readFileSync(ENV_FILE, 'utf8'))
  : {};

const apiUrl =
  process.env.FRONTEND_API_URL ||
  env.FRONTEND_API_URL ||
  'https://api.skiltak.com/api';

const contents = `// Generado por scripts/build-env.js — NO editar a mano.
export const environment = {
  production: true,
  apiUrl: '${apiUrl}'
};
`;

fs.mkdirSync(path.dirname(OUT_FILE), { recursive: true });
fs.writeFileSync(OUT_FILE, contents);
console.log(`[build-env] environment.prod.ts -> apiUrl=${apiUrl}`);
