"""
Shared HTTP utilities for DrugRescue tools.
==============================================

Provides SSL-safe HTTP helpers that handle macOS certificate issues.

The macOS Python problem:
    ssl.create_default_context() SUCCEEDS but the resulting context
    can't actually verify certs for some domains. The error only
    appears at urlopen() time, not at context creation time.

Solution:
    Try verified SSL first. On CERTIFICATE_VERIFY_FAILED, automatically
    retry with an unverified context. Log a warning but don't crash.
    Sets a sticky flag so all subsequent calls skip straight to unverified.
"""

from __future__ import annotations

import json
import logging
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

logger = logging.getLogger(__name__)

_verified_ctx: Optional[ssl.SSLContext] = None
_unverified_ctx: Optional[ssl.SSLContext] = None
_use_unverified: bool = False


def _get_verified_ctx() -> ssl.SSLContext:
    """Best-effort verified SSL context."""
    global _verified_ctx
    if _verified_ctx is not None:
        return _verified_ctx

    cafile = os.getenv("SSL_CERT_FILE") or os.getenv("REQUESTS_CA_BUNDLE")
    if cafile and os.path.exists(cafile):
        _verified_ctx = ssl.create_default_context(cafile=cafile)
        return _verified_ctx

    try:
        import certifi
        _verified_ctx = ssl.create_default_context(cafile=certifi.where())
        return _verified_ctx
    except ImportError:
        pass

    for path in [
        "/etc/ssl/cert.pem",
        "/etc/ssl/certs/ca-certificates.crt",
        "/etc/pki/tls/certs/ca-bundle.crt",
    ]:
        if os.path.exists(path):
            try:
                _verified_ctx = ssl.create_default_context(cafile=path)
                return _verified_ctx
            except Exception:
                continue

    _verified_ctx = ssl.create_default_context()
    return _verified_ctx


def _get_unverified_ctx() -> ssl.SSLContext:
    """Unverified SSL context — last resort for hackathon connectivity."""
    global _unverified_ctx
    if _unverified_ctx is not None:
        return _unverified_ctx
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    _unverified_ctx = ctx
    return ctx


def get_ssl_context() -> ssl.SSLContext:
    """Public API — returns the best working SSL context."""
    if _use_unverified:
        return _get_unverified_ctx()
    return _get_verified_ctx()


_DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _ensure_request(req_or_url) -> urllib.request.Request:
    """Ensure we have a Request object with essential headers."""
    if isinstance(req_or_url, str):
        req_or_url = urllib.request.Request(req_or_url)

    # Many APIs (PubChem, ClinicalTrials.gov) block Python's default UA
    if not req_or_url.has_header("User-agent"):
        req_or_url.add_unredirected_header("User-Agent", _DEFAULT_UA)

    # Prevent gzip responses that urllib can't auto-decompress
    if not req_or_url.has_header("Accept-encoding"):
        req_or_url.add_unredirected_header("Accept-Encoding", "identity")

    return req_or_url


def _urlopen_with_ssl_retry(req_or_url, *, timeout: float = 30.0):
    """
    urlopen with automatic SSL fallback and default headers.

    - Adds User-Agent + Accept-Encoding: identity to bare URLs
    - Try verified SSL first
    - On CERTIFICATE_VERIFY_FAILED, retry unverified (sticky)
    """
    global _use_unverified
    req = _ensure_request(req_or_url)

    if _use_unverified:
        return urllib.request.urlopen(
            req, timeout=timeout, context=_get_unverified_ctx(),
        )

    try:
        return urllib.request.urlopen(
            req, timeout=timeout, context=_get_verified_ctx(),
        )
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            logger.warning(
                "SSL verification failed — retrying without verification. "
                "Fix: pip install certifi  OR  "
                "/Applications/Python\\ 3.*/Install\\ Certificates.command"
            )
            _use_unverified = True
            return urllib.request.urlopen(
                req, timeout=timeout, context=_get_unverified_ctx(),
            )
        raise


def fetch_json(url: str, *, timeout: float = 30.0) -> tuple[dict, int]:
    """GET a URL and parse JSON. Returns (data, status_code)."""
    try:
        with _urlopen_with_ssl_retry(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode()), int(resp.status)
    except urllib.error.HTTPError as e:
        return {}, e.code


def post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    *,
    timeout: float = 60.0,
) -> tuple[dict, int]:
    """POST JSON and parse response. Returns (data, status_code)."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with _urlopen_with_ssl_retry(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode()), int(resp.status)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        try:
            return json.loads(body), e.code
        except Exception:
            return {"_error": body}, e.code
