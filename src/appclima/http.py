"""Cliente HTTP compartido.

Un solo sitio donde viven timeouts, reintentos y User-Agent. Las APIs públicas
devuelven 429 y 5xx con más frecuencia de la que uno espera, así que el retry
con backoff exponencial no es opcional: es la diferencia entre un pipeline que
aguanta y uno que se cae de madrugada sin que nadie lo vea.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from appclima.config import settings

log = logging.getLogger(__name__)

# Códigos que merece la pena reintentar. Un 404 o un 400 no se arreglan
# insistiendo: son bugs nuestros y deben fallar rápido y ruidosamente.
RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


class RetryableHTTPError(Exception):
    """Fallo transitorio: merece otro intento."""


def _retry_after_seconds(response: httpx.Response) -> float | None:
    """Lee la cabecera Retry-After. Puede venir en segundos o como fecha HTTP."""
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        # Formato de fecha HTTP: no merece la pena parsearlo, devolvemos una
        # espera conservadora y que el backoff exponencial haga el resto.
        return 30.0


def _client(extra_headers: dict[str, str] | None = None) -> httpx.Client:
    headers = {"User-Agent": settings.user_agent, "Accept": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    return httpx.Client(
        headers=headers,
        timeout=settings.request_timeout,
        follow_redirects=True,
    )


@retry(
    retry=retry_if_exception_type((RetryableHTTPError, httpx.TransportError)),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    stop=stop_after_attempt(settings.max_retries),
    reraise=True,
)
def get_json(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    """GET que devuelve JSON, con reintentos sobre fallos transitorios."""
    with _client(headers) as client:
        response = client.get(url, params=params)

        if response.status_code in RETRYABLE_STATUS:
            # Si el servidor nos dice cuánto esperar, le hacemos caso. Ignorar
            # Retry-After en un 429 es la forma más rápida de que te bloqueen
            # la IP en una API pública y gratuita.
            wait_hint = _retry_after_seconds(response)
            if wait_hint:
                log.warning(
                    "%s en %s — el servidor pide esperar %.0fs",
                    response.status_code, response.url, wait_hint,
                )
                time.sleep(min(wait_hint, 120))
            else:
                log.warning(
                    "Fallo transitorio %s en %s — reintentando",
                    response.status_code, response.url,
                )
            raise RetryableHTTPError(f"{response.status_code} en {response.url}")

        response.raise_for_status()
        return response.json()
