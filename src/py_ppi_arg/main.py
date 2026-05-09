from typing import Any, Callable, Dict, List, Optional, Tuple
import base64
import json
import warnings

from .components import (
    RestClient,
    ApiException,
    urls,
    clientKey,
    InstrumentType,
    Settlement,
    OperationType
)


class PPI:
    def __init__(self, user: str, password: str,
                 otp_provider: Optional[Callable[[], str]] = None,
                 remember_device: bool = False,
                 ) -> None:
        ## Parameters validation
        required_fields: list[tuple[str, Any, Any]]  = [
            ("user", user, str),
            ("password", password, str),
        ]
        # self._check_fields(required_fields)

        ## REST Client
        self.client: RestClient = RestClient()
        self.clientKeyheader: clientKey = clientKey().get_client_keys()

        ## Enums as instance variables
        self.instrument_types = InstrumentType
        self.settlements = Settlement
        self.operation_types = OperationType

        ## Login Information
        self.user: str = user
        self.password: str = password
        self.otp_provider: Optional[Callable[[], str]] = otp_provider
        self.remember_device: bool = remember_device

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
            "Content-Type": "application/json",
            "Clientkey": self.clientKeyheader["ClientKey"],
            "Authorizedclient": self.clientKeyheader["AuthorizedClient"],
        }

        ## Finally, tries to authenticate
        self._auth()
    def _auth(self) -> None:

        """Calls the PPI API method to get an access token and updates the session headers.

        This method is responsible for authenticating the user by obtaining an access token from the PPI API.
        It then updates the session headers with the obtained token for subsequent API requests.

        If the account has 2FA enabled, it will also call the 2FA validation endpoint using the OTP code
        obtained from `otp_provider` (or `input()` as a fallback).

        Raises:
            ApiException: If the credentials are invalid or the access token cannot be obtained.
        """

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
        """Prompts for the OTP code and posts it to the 2FA validation endpoint.

        Args:
            login_payload: The `payload` object returned by the Login endpoint when 2FA is required.

        Returns:
            The full ValidateUser2FA response dict.
        """
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
        
        """Updates the session headers and performs additional steps after login.

        After successful login and obtaining the access token, this method is responsible for updating the session headers
        with the necessary authentication information. It replicates the workflow of the web app.

        """
        
        headers_update: dict[str, str] = {
            "authorization": f"bearer {self.access_token}",
        }
        # print(headers_update)
        self.headers.update(headers_update)
    
    def get_tickers_list(self,
        instrument_type: InstrumentType,
        operation_type: OperationType,
        settlement: Settlement) -> dict[str,Any]:
        
        """Takes a request to get instruments quote list information filtered by instrument type, operation type and settlement
        
        Args:
            client_ID (str): string with client ID
            instrument_type (str): InstrumentType of instrument
            operation_type (str): OperationType for instrument
            settlement (str): Settlement for instrument

        Returns:
            dict: Dict with the instruments information
        """
        
        return self.client.get_tickers_list(
            self.headers, self.clientID, instrument_type.value, operation_type.value, settlement.value
        )
                
    def search_tickers(self, short_ticker: Optional[str] = None, item_id: Optional[str] = None) -> dict[str,any]:
        
        """Makes a request to the api to get the information for a ticker

        Args:
            headers (dict[str,Any]): headers for the client that permits the request
            short_ticker (str): String with the short_ticker. Example: "DNC3"
            item_id (str). Example: "885981"

        Returns:
            dict: Dict with the instrument information
            
        Note:
            Should look for the short ticker or for the item_id, not both
        """
        return self.client.search_tickers(
            headers = self.headers,
            short_ticker=short_ticker,
            item_id=item_id
        )
        
    def get_technical_data_bonds(self, settlement: Settlement, item_id: str):
        
        """Takes a request to get techical data for a bond
        
        Args:
            settlement (str): Settlement for instrument
            item_id (str). Example: "885981"

        Returns:
            dict: Dict with the instruments information
        """
        
        return self.client.get_technical_data_bonds(self.headers, settlement.value, item_id)
    
    def get_historic_data(self, item_id: str, settlement: Settlement, 
                        date_from: Optional[str] = "", date_to: Optional[str] = "") -> dict[str, Any]:
        """Makes a request to the api to get the historic data for an item

        Args:
            headers (dict[str,Any]): headers for the client that permits the request
            item_id (str). Example: "885981"
            settlement (str, optional): Settlement of instrument
            date_from (str, optional): Start date. Format yyyy-MM-dd
            date_to (str, optional): End date. Format yyyy-MM-dd
        Returns:
            dict: Dict with the instrument historic information
            
        """

        return self.client.get_historic_data(self.headers, item_id, settlement.value, date_from, date_to)
    
    def get_intraday_data(self, item_id: str, settlement: Settlement, 
                        ) -> dict[str, Any]:
        """Makes a request to the api to get the intraday data for an item

        Args:
            headers (dict[str,Any]): headers for the client that permits the request
            item_id (str). Example: "885981"
            settlement (str, optional): Settlement of instrument
        Returns:
            dict: Dict with the instrument intraday information
            
        """

        return self.client.get_intraday_data(self.headers, item_id, settlement.value)