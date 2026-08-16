"""Server-side verification of Google / Apple OAuth tokens.

Without this, POST /auth/google|apple would mint a session for anyone who
knows a victim's email + provider sub. The mobile app already sends
id_token (Google) / identityToken (Apple), so we verify them here.

Set OAUTH_VERIFY=off to skip verification (local dev / tests only).
"""
import os
import logging
import requests
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Fallbacks match the client IDs baked into mobile/lib/services/auth_service.dart.
# Google id_token aud is the serverClientId (= web client id) on Android,
# or the iOS client id on iOS, so both must be accepted.
# ⚠️ 重跑 flutterfire configure（換 bundle id / package name）後 Firebase 會發新的
#    iOS client id，這兩個 fallback 就失效 —— 用 GOOGLE_OAUTH_CLIENT_IDS 帶新值，
#    前端對應的是 auth_service.dart 的 --dart-define。
_DEFAULT_GOOGLE_AUDIENCES = (
    # web client id：Web 登入的 aud，也是 Android 的 serverClientId
    "200440251043-ro7dokuob1oc08jbl04fnage0k3iegd7.apps.googleusercontent.com",
    # iOS client id
    "200440251043-b4g319nurnqt9483nh963qo1gqarqpi7.apps.googleusercontent.com",
)
# Apple id_token 的 aud 就是 iOS bundle id，改 bundle id 一定要同步改這裡
_DEFAULT_APPLE_BUNDLE_ID = "com.schedulo.app"

_APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
_apple_jwks_cache: dict = {}


def _verify_enabled() -> bool:
    return os.getenv("OAUTH_VERIFY", "on").lower() not in ("off", "0", "false")


def _check_sub_email(claims: dict, expected_sub: str, expected_email) -> None:
    if claims.get("sub") != expected_sub:
        raise HTTPException(status_code=401, detail="Token subject mismatch")
    token_email = claims.get("email")
    # Apple only returns email on first sign-in; compare only when both present.
    if expected_email and token_email and token_email.lower() != expected_email.lower():
        raise HTTPException(status_code=401, detail="Token email mismatch")


def verify_google_id_token(id_token: str, expected_sub: str, expected_email) -> None:
    """Validate a Google id_token via Google's tokeninfo endpoint.

    tokeninfo checks signature and expiry; we additionally check aud/sub/email.
    Raises HTTPException(401) on any mismatch.
    """
    if not _verify_enabled():
        logger.warning("OAUTH_VERIFY=off — skipping Google id_token verification")
        return
    if not id_token:
        raise HTTPException(status_code=401, detail="Missing Google id_token")

    try:
        resp = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
            timeout=10,
        )
    except requests.RequestException as e:
        logger.error(f"Google tokeninfo unreachable: {e}")
        raise HTTPException(status_code=503, detail="無法驗證 Google 登入，請稍後再試")

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google id_token")

    claims = resp.json()
    allowed = {
        a.strip()
        for a in os.getenv(
            "GOOGLE_OAUTH_CLIENT_IDS", ",".join(_DEFAULT_GOOGLE_AUDIENCES)
        ).split(",")
        if a.strip()
    }
    if claims.get("aud") not in allowed:
        # 印出實際 aud：換 Firebase app 之後這裡會整批 401，沒有這行只能盲猜
        logger.error(
            f"Google id_token aud={claims.get('aud')} 不在允許清單內 "
            f"（目前允許 {sorted(allowed)}）—— 檢查 GOOGLE_OAUTH_CLIENT_IDS"
        )
        raise HTTPException(status_code=401, detail="Google id_token audience mismatch")
    _check_sub_email(claims, expected_sub, expected_email)


def _get_apple_jwks(force_refresh: bool = False) -> dict:
    global _apple_jwks_cache
    if force_refresh or not _apple_jwks_cache:
        resp = requests.get(_APPLE_JWKS_URL, timeout=10)
        resp.raise_for_status()
        _apple_jwks_cache = resp.json()
    return _apple_jwks_cache


def verify_apple_identity_token(identity_token: str, expected_sub: str, expected_email) -> None:
    """Validate an Apple identityToken (JWT) against Apple's public JWKS.

    Raises HTTPException(401) on any mismatch.
    """
    if not _verify_enabled():
        logger.warning("OAUTH_VERIFY=off — skipping Apple identityToken verification")
        return
    if not identity_token:
        raise HTTPException(status_code=401, detail="Missing Apple identityToken")

    from jose import jwt as jose_jwt
    from jose.exceptions import JWTError

    audience = os.getenv("APPLE_BUNDLE_ID", _DEFAULT_APPLE_BUNDLE_ID)
    try:
        kid = jose_jwt.get_unverified_header(identity_token).get("kid")
        key = next(
            (k for k in _get_apple_jwks().get("keys", []) if k.get("kid") == kid),
            None,
        )
        if key is None:
            # Apple rotates keys — refetch once before giving up.
            key = next(
                (k for k in _get_apple_jwks(force_refresh=True).get("keys", []) if k.get("kid") == kid),
                None,
            )
        if key is None:
            raise HTTPException(status_code=401, detail="Unknown Apple signing key")
        claims = jose_jwt.decode(
            identity_token,
            key,
            algorithms=["RS256"],
            audience=audience,
            issuer="https://appleid.apple.com",
        )
    except HTTPException:
        raise
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid Apple identityToken")
    except requests.RequestException as e:
        logger.error(f"Apple JWKS unreachable: {e}")
        raise HTTPException(status_code=503, detail="無法驗證 Apple 登入，請稍後再試")

    _check_sub_email(claims, expected_sub, expected_email)
