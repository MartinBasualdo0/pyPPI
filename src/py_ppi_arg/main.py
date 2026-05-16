from typing import Any, Callable, Dict, List, Optional, Tuple
import base64
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
        3. Full login with user/password (may require 2FA)
        """
        if self.cache_session and self._restore_from_cache():
            return

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

    def _restore_from_cache(self) -> bool:
        """Tries to restore a previous session from disk. Returns True if successful."""
        if not _SESSION_FILE.exists():
            return False
        try:
            cache = json.loads(_SESSION_FILE.read_text())
        except Exception:
            return False

        user_hash = hashlib.sha256(self.user.encode()).hexdigest()
        if cache.get("user_hash") != user_hash:
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

    def _token_is_valid(self, token: str) -> bool:
        try:
            claims = self._decode_jwt_claims(token)
            return claims.get("exp", 0) > time.time() + 60
        except Exception:
            return False

    def _save_session(self, token: dict, client_id: Optional[str] = None) -> None:
        cache = {
            "user_hash": hashlib.sha256(self.user.encode()).hexdigest(),
            "access_token": self.access_token,
            "refresh_token": token.get("refreshToken"),
            "client_id": client_id if client_id is not None else self.clientID,
            "clientkey": self.clientkey,
        }
        try:
            _SESSION_FILE.write_text(json.dumps(cache))
            _SESSION_FILE.chmod(0o600)
        except Exception:
            pass

    def _resolve_client_id(self) -> Optional[str]:
        """Resolves the user's cuentaID for account-context endpoints.

        Tries the legacy ComitentesAsignados endpoint first; if it fails
        (PPI has restricted it for some accounts), falls back to extracting
        `PPAuth.Claims.General.Cuentas` from the JWT.

        Returns None if neither source yields a value — account-context
        endpoints (e.g. get_tickers_list) won't work, but market-data
        endpoints will.
        """
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
        """Prompts for the OTP code and posts it to the 2FA validation endpoint."""
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

    def get_tickers_list(self,
        instrument_type: InstrumentType,
        operation_type: OperationType,
        settlement: Settlement) -> dict[str, Any]:
        """Retrieves instruments quote list filtered by instrument type, operation type and settlement."""
        return self.client.get_tickers_list(
            self.headers, self.clientID, instrument_type.value, operation_type.value, settlement.value
        )

    def search_tickers(self, short_ticker: Optional[str] = None, item_id: Optional[str] = None) -> dict[str, any]:
        """Searches for an instrument by short ticker or internal item ID."""
        return self.client.search_tickers(
            headers=self.headers,
            short_ticker=short_ticker,
            item_id=item_id
        )

    def get_technical_data_bonds(self, settlement: Settlement, item_id: str):
        """Retrieves technical data for a bond (TIR, duration, parity, etc.)."""
        return self.client.get_technical_data_bonds(self.headers, settlement.value, item_id)

    def get_historic_data(self, item_id: str, settlement: Settlement,
                        date_from: Optional[str] = "", date_to: Optional[str] = "") -> dict[str, Any]:
        """Retrieves historical price data for an instrument."""
        return self.client.get_historic_data(self.headers, item_id, settlement.value, date_from, date_to)

    def get_intraday_data(self, item_id: str, settlement: Settlement) -> dict[str, Any]:
        """Retrieves intraday price data for an instrument."""
        return self.client.get_intraday_data(self.headers, item_id, settlement.value)
