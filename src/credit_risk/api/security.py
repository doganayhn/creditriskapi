"""Single configured credential; only its non-secret ID enters audit records."""

import hmac


def valid_api_key(supplied: bytes, configured: str) -> bool:
    return hmac.compare_digest(supplied, configured.encode("utf-8"))
