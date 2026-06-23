#!/usr/bin/env node
/**
 * Wrapper para arrancar el backend Django desde npm scripts.
 *
 * El motivo: pasar el path al Python del venv directo desde el
 * package.json fallaba según el shell donde npm levantara el script:
 *   - bash (Git Bash):  `env/Scripts/python` → bash interpretaba
 *     `env` como el built-in command `env`
 *   - cmd.exe:          `./env/Scripts/python.exe` → cmd no soporta `./`
 *   - alternativas con backslashes rompían bash
 *
 * Acá llamamos a `child_process.spawn` directamente con un path
 * absoluto resuelto por Node — sin shell parsing en el medio. Funciona
 * idéntico en cmd, PowerShell, bash, zsh, fish, da igual.
 */
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const ROOT = path.resolve(__dirname, '..');
const BACKEND = path.join(ROOT, 'backend');

const isWin = process.platform === 'win32';
const pythonPath = isWin
  ? path.join(BACKEND, 'env', 'Scripts', 'python.exe')
  : path.join(BACKEND, 'env', 'bin', 'python');

if (!fs.existsSync(pythonPath)) {
  console.error('[start-backend] No encontré el venv en:', pythonPath);
  console.error('[start-backend] Creá uno con:');
  console.error('  cd backend && python -m venv env');
  console.error('  env/Scripts/pip install -r requirements.txt  (o requirements-prod.txt)');
  process.exit(1);
}

const proc = spawn(pythonPath, ['manage.py', 'runserver', '0.0.0.0:8000'], {
  cwd: BACKEND,
  stdio: 'inherit',
});

proc.on('error', (err) => {
  console.error('[start-backend] Falló al spawnear Python:', err.message);
  process.exit(1);
});

proc.on('exit', (code) => {
  process.exit(code ?? 0);
});

// Forward de señales para que Ctrl+C cierre el child limpio
['SIGINT', 'SIGTERM'].forEach((sig) => {
  process.on(sig, () => proc.kill(sig));
});
