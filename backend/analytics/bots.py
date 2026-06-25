"""Filtro de bots para no contaminar las métricas.

Estrategia: regex sobre el User-Agent. Es heurística pero captura ~99%
del tráfico de crawlers conocidos. Si un bot evade el filter, podemos
identificarlo retroactivamente desde `AnalyticsEvent.user_agent` y
purgarlo.

Una solución más robusta (UA database tipo `crawler-user-agents`)
agrega 200KB de deps; lo evitamos hasta que sea problema real.
"""

from __future__ import annotations

import re

# Patterns conocidos. Lista chica, fácil de ampliar. Insensible a caso.
_BOT_PATTERNS = re.compile(
    r"\b("
    r"googlebot|bingbot|baiduspider|yandexbot|duckduckbot|"
    r"ahrefsbot|semrushbot|mj12bot|dotbot|petalbot|"
    r"facebookexternalhit|twitterbot|linkedinbot|"
    r"slackbot|discordbot|telegrambot|whatsapp|"
    r"applebot|bytespider|crawler|spider|scraper|"
    r"headlesschrome|phantomjs|puppeteer|playwright|selenium|"
    r"curl|wget|python-requests|python-urllib|go-http-client|"
    r"axios|node-fetch"
    r")\b",
    re.IGNORECASE,
)


def is_bot(user_agent: str | None) -> bool:
    """True si el UA parece bot/crawler/herramienta automatizada.

    `None` o vacío también se consideran bot — un browser real siempre
    manda UA. Evita que scripts que omiten headers ensucien las
    métricas.
    """
    if not user_agent:
        return True
    return bool(_BOT_PATTERNS.search(user_agent))
