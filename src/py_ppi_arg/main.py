from typing import Any, Callable, Dict, List, Optional
import base64
import http.cookiejar as _cookiejar
import json
import time
import hashlib
import warnings
from pathlib import Path

from .components import (
    RestClient,
    ApiException,
    urls,
    clientKey,
    InstrumentType,
    Settlement,
    OperationType
)

_SESSION_FILE = Path.home() / ".py_ppi_arg_session.json"


def _serialize_cookies(jar) -> list:
    """Serializa un CookieJar a una lista JSON-safe con dominio, path y expires."""
    result = []
    for c in jar:
        result.append({
            "name": c.name,
            "value": c.value,
            "domain": c.domain,
            "path": c.path,
            "expires": c.expires,
            "secure": c.secure,
            "rest": dict(c._rest) if hasattr(c, "_rest") else {},
        })
    return result


def _restore_cookies(jar, cookies: list) -> None:
    """Restaura cookies serializadas en un CookieJar con todos sus atributos."""
    for c in cookies:
        domain = c.get("domain", "")
        jar.set_cookie(_cookiejar.Cookie(
            version=0,
            name=c["name"],
            value=c["value"],
            port=None, port_specified=False,
            domain=domain,
            domain_specified=bool(domain),
            domain_initial_dot=domain.startswith("."),
            path=c.get("path", "/"),
            path_specified=bool(c.get("path")),
            secure=c.get("secure", False),
            expires=c.get("expires"),
            discard=c.get("expires") is None,
            comment=None, comment_url=None,
            rest=c.get("rest", {}),
        ))


class PPI:
    def __init__(self, user: str, password: str,
                 otp_provider: Optional[Callable[[], str]] = None,
                 remember_device: bool = False,
                 cache_session: bool = True,
                 ) -> None:
        self.client: RestClient = RestClient()
        self.clientKeyheader: clientKey = clientKey().get_client_keys()

        self.instrument_types = InstrumentType
        self.settlements = Settlement
        self.operation_types = OperationType

        self.user: str = user
        self.password: str = password
        self.otp_provider: Optional[Callable[[], str]] = otp_provider
        self.remember_device: bool = remember_device
        self.cache_session: bool = cache_session

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
            "Content-Type": "application/json",
            "Clientkey": self.clientKeyheader["ClientKey"],
            "Authorizedclient": self.clientKeyheader["AuthorizedClient"],
        }

        self._auth()

    def _auth(self) -> None:
        """Authenticates against PPI, reusing a cached session when possible.

        Order of attempts:
        1. Valid cached access token (no network call needed)
        2. Cached refresh token (one network call, no 2FA)
        3. Full login — cookies are restored first so PPI skips 2FA
           if this device was previously marked as trusted via remember_device=True
        """
        cache = self._load_cache()

        # Restore cookies before any login attempt so PPI recognizes the device
        # and skips 2FA even on a full re-login
        if cache:
            self._apply_cached_cookies(cache)

        if cache and self._restore_from_cache(cache):
            return

        # Full login
        payload: str = json.dumps({"usuario": self.user, "clave": self.password})
        response: Dict[str, Any] = self.client.get_token(data=payload, headers=self.headers)

        if response["status"] != 0:
            raise ApiException(f'Login failed: {response.get("message")}')

        login_payload: Dict[str, Any] = response["payload"]

        if login_payload.get("twoFAInfo") and not login_payload.get("token"):
            response = self._complete_2fa(login_payload)
            if response["status"] != 0:
                raise ApiException(f'2FA validation failed: {response.get("message")}')
            login_payload = response["payload"]

        token = login_payload.get("token")
        if not token or "accessToken" not in token:
            raise ApiException("Access token not found in the API response")

        self.access_token = token["accessToken"]
        self.clientkey = token["clienteID"]
        self._auth_phase_2()
        self.clientID = self._resolve_client_id()

        if self.cache_session:
            self._save_session(token)

    # ------------------------------------------------------------------ cache

    def _load_cache(self) -> Optional[Dict]:
        if not self.cache_session or not _SESSION_FILE.exists():
            return None
        try:
            return json.loads(_SESSION_FILE.read_text())
        except Exception:
            return None

    def _user_hash(self) -> str:
        return hashlib.sha256(self.user.encode()).hexdigest()

    def _apply_cached_cookies(self, cache: Dict) -> None:
        if cache.get("user_hash") != self._user_hash():
            return
        cookies = cache.get("cookies", {})
        if isinstance(cookies, list):
            _restore_cookies(self.client.session.cookies, cookies)
        else:
            # Formato legacy {name: value} — compatibilidad con cachés anteriores
            for name, value in cookies.items():
                self.client.session.cookies.set(name, value)

    def _restore_from_cache(self, cache: Dict) -> bool:
        if cache.get("user_hash") != self._user_hash():
            return False

        access_token = cache.get("access_token")
        if access_token and self._token_is_valid(access_token):
            self.access_token = access_token
            self.clientkey = cache.get("clientkey", "")
            self.clientID = cache.get("client_id")
            self._auth_phase_2()
            return True

        refresh_token = cache.get("refresh_token")
        if refresh_token:
            try:
                response = self.client.refresh_token(refresh_token, self.headers)
                token = response.get("payload", {}).get("token", {})
                if token and "accessToken" in token:
                    self.access_token = token["accessToken"]
                    self.clientkey = token.get("clienteID", cache.get("clientkey", ""))
                    self.clientID = cache.get("client_id")
                    self._auth_phase_2()
                    self._save_session(token, client_id=self.clientID)
                    return True
            except Exception:
                pass

        return False

    def _save_session(self, token: Dict, client_id: Optional[str] = None) -> None:
        cache = {
            "user_hash": self._user_hash(),
            "access_token": self.access_token,
            "refresh_token": token.get("refreshToken"),
            "client_id": client_id if client_id is not None else self.clientID,
            "clientkey": self.clientkey,
            "cookies": _serialize_cookies(self.client.session.cookies),
        }
        try:
            _SESSION_FILE.write_text(json.dumps(cache))
            _SESSION_FILE.chmod(0o600)
        except Exception:
            pass

    def _token_is_valid(self, token: str) -> bool:
        try:
            claims = self._decode_jwt_claims(token)
            return claims.get("exp", 0) > time.time() + 60
        except Exception:
            return False

    # --------------------------------------------------------------- auth flow

    def _resolve_client_id(self) -> Optional[str]:
        try:
            return self.client.get_client_id(self.headers)
        except ApiException:
            pass
        try:
            jwt_claims = self._decode_jwt_claims(self.access_token)
            return jwt_claims.get("PPAuth.Claims.General.Cuentas")
        except Exception:
            warnings.warn(
                "Could not resolve cuentaID. Account-context endpoints will not work, "
                "but market-data endpoints (search_tickers, get_historic_data, etc.) will."
            )
            return None

    @staticmethod
    def _decode_jwt_claims(token: str) -> Dict[str, Any]:
        payload_segment = token.split(".")[1]
        padding = 4 - len(payload_segment) % 4
        if padding < 4:
            payload_segment += "=" * padding
        return json.loads(base64.urlsafe_b64decode(payload_segment))

    def _complete_2fa(self, login_payload: Dict[str, Any]) -> Dict[str, Any]:
        if self.otp_provider is not None:
            code: str = self.otp_provider()
        else:
            code = input("Ingresá el código de 2FA enviado por PPI: ").strip()

        body: str = json.dumps({
            "userId": login_payload["usuario"]["id"],
            "codigo": code,
            "recordar": self.remember_device,
            "twoFactType": login_payload["twoFAInfo"]["twoFactorType"],
        })
        return self.client.validate_2fa(data=body, headers=self.headers)

    def _auth_phase_2(self) -> None:
        self.headers.update({"authorization": f"bearer {self.access_token}"})

    # ----------------------------------------------------------- public methods

    def get_tickers_list(self,
        instrument_type: InstrumentType,
        operation_type: OperationType,
        settlement: Settlement) -> Dict[str, Any]:
        """Retrieves instruments quote list filtered by instrument type, operation type and settlement."""
        return self.client.get_tickers_list(
            self.headers, self.clientID, instrument_type.value, operation_type.value, settlement.value
        )

    def search_tickers(self, short_ticker: Optional[str] = None, item_id: Optional[str] = None) -> Dict[str, Any]:
        """Searches for an instrument by short ticker or internal item ID."""
        return self.client.search_tickers(
            headers=self.headers,
            short_ticker=short_ticker,
            item_id=item_id
        )

    def get_technical_data_bonds(self, settlement: Settlement, item_id: str) -> Dict[str, Any]:
        """Retrieves technical data for a bond (TIR, duration, parity, etc.)."""
        return self.client.get_technical_data_bonds(self.headers, settlement.value, item_id)

    def get_historic_data(self, item_id: str, settlement: Settlement,
                        date_from: Optional[str] = "", date_to: Optional[str] = "") -> Dict[str, Any]:
        """Retrieves historical price data for an instrument."""
        return self.client.get_historic_data(self.headers, item_id, settlement.value, date_from, date_to)

    def get_intraday_data(self, item_id: str, settlement: Settlement) -> Dict[str, Any]:
        """Retrieves intraday price data for an instrument."""
        return self.client.get_intraday_data(self.headers, item_id, settlement.value)
