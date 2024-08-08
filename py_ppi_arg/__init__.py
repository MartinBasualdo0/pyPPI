from typing import Any, Dict, List, Optional, Tuple
import json

from py_ppi_arg.src.components import (
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
                #  gotrue_meta_security: Optional[Dict[str, Any]] = {}, api_key: Optional[str] = None
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

        Raises:
            Exception: If there is an error during the authentication process.
            Exception: If the access token is not found in the API response.
        """
        
        payload: str = json.dumps({"usuario": self.user, "clave": self.password})
        # self.client.update_session_headers(self.headers)
        # print(self.headers)
        response: Dict[str, Any] = self.client.get_token(data=payload, headers=self.headers)
        # print(response)
        if response["status"] != 0:
            raise Exception(f'Error: {response["message"]}')

        if "accessToken" not in response["payload"]["token"]:
            raise Exception("Error: Access token not found in the API response")

        self.access_token = response["payload"]["token"]["accessToken"]
        self.clientkey = response["payload"]["token"]["clienteID"]
        self._auth_phase_2()
        self.clientID = self.client.get_client_id(self.headers)
        
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