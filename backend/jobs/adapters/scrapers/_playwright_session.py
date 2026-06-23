"""Wrapper de Playwright para scrapers que necesitan JS rendering.

Algunos portales (Magneto, Indeed) son SPAs sin SSR o tienen anti-bot
de Cloudflare que requiere un browser real para resolver el challenge.
Para esos, plain `requests` no alcanza — necesitamos lanzar Chromium
headless via Playwright.

Diseño:
  - Import perezoso de `playwright.sync_api` dentro de la función,
    no a module-load. Si Playwright no está instalado en este entorno
    (ej. CI sin Chromium), los demás scrapers no rompen.
  - Browser cerrado SIEMPRE al final via try/finally — sin esto los
    procesos zombie de Chromium se acumulan y consumen toda la RAM.
  - User-agent + viewport configurables para parecer un Chrome normal.

Costo en RAM por sesión: ~300-500MB peak. Cerrar al terminar libera todo.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

logger = logging.getLogger(__name__)


_VIEWPORT = {"width": 1280, "height": 800}
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


@contextmanager
def playwright_page(timeout_ms: int = 30000) -> Iterator:
    """Context manager que abre Chromium headless, devuelve un Page, y
    cierra todo al final (incluso si tira excepción).

    Yields:
        playwright.sync_api.Page listo para `.goto(...)`.

    Raises:
        ImportError: si `playwright` no está instalado en el venv.
            El scraper caller debe handle-arlo y caer al fallback.
        Exception: lo que Chromium tire al lanzarse (Chromium binary
            faltante → "Executable doesn't exist"; instalá con
            `python -m playwright install chromium`).
    """
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    browser = None
    context = None
    try:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",  # requerido en algunos VPS / containers
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",  # /dev/shm chico en VPS shared
            ],
        )
        context = browser.new_context(
            user_agent=_USER_AGENT,
            viewport=_VIEWPORT,
            locale="es-CO",
            timezone_id="America/Bogota",
            # Disabling images saves 30-40% bandwidth y RAM, no necesitamos
            # ver las fotos de los job posts para parsear texto.
            java_script_enabled=True,
        )
        page = context.new_page()
        page.set_default_timeout(timeout_ms)
        yield page
    finally:
        # Cleanup en cascada — si browser.close() falla, igual queremos
        # pw.stop(). Try individualmente.
        if context is not None:
            try:
                context.close()
            except Exception:
                logger.exception("Failed to close playwright context")
        if browser is not None:
            try:
                browser.close()
            except Exception:
                logger.exception("Failed to close playwright browser")
        try:
            pw.stop()
        except Exception:
            logger.exception("Failed to stop playwright")
