from typing import Any, Dict, List, Optional
import requests
import simplejson
from datetime import datetime

from . import urls
from .exceptions import ApiException


class RestClient:
    def __init__(self):
        self.session = requests.Session()
        self.messages: List[Dict[str, str]] = []

    def get_token(self, data: str, headers: dict[str,str]) -> Dict[str, Any]:
        """Makes a request to the api to get an access token

        Args:
            data (str): String with email and password
            headers (dict[str,str]): headers for the client that permits the request

        Returns:
            dict: Dict with token and user data
        """
        return self.api_request(
            urls.endpoints["token"], method="post", 
            headers=headers,
            # params=params, #it does not need it apparently
            data=data
        )
    
    def get_client_id(self, headers: dict[str,Any]) -> Dict[str,Any]:
        """Makes a request to the api to get the client_id

        Args:
            headers (dict[str,Any]): headers for the client that permits the request

        Returns:
            Str: String with client ID
        """
        return self.api_request(
            urls.endpoints["cuenta_ID"],
            headers
        )["payload"][0]["id"]
        
    def get_tickers_list(self,
        headers: dict[str,str],
        client_ID:str, 
        instrument_type:str,
        operation_type:str,
        settlement:str) -> dict[str,Any]:
        """Takes a request to get instruments quote list information filtered by instrument type, operation type and settlement
        
        Args:
            headers (dict[str,Any]): headers for the client that permits the request
            client_ID (str): string with client ID
            instrument_type (str): InstrumentType of instrument
            settlement (str): Settlement of instrument

        Returns:
            dict: Dict with the instruments information
        """
        
        return self.api_request(
            urls.endpoints["tickers_list"].format(
                client_ID, instrument_type, operation_type, settlement
                ),
            headers=headers
        )
    
    def search_tickers(self, headers: dict[str,str], short_ticker:Optional[str], item_id:Optional[str]) -> dict[str,Any]:
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
        if short_ticker and item_id:
            print("Should look for the short ticker or for the item_id, not both")
        
        search_parameter = short_ticker if short_ticker else item_id
        
        return self.api_request(
            urls.endpoints["ticker_search"].format(search_parameter),
            headers=headers
        )
    
    def get_technical_data_bonds(self, headers: dict[str,str], settlement:str, item_id:str) -> dict[str,Any]:
        """Makes a request to the api to get the technical data for bonds

        Args:
            headers (dict[str,Any]): headers for the client that permits the request
            item_id (str). Example: "885981"
            settlement (str): Settlement of instrument

        Returns:
            dict: Dict with the instrument information
            
        """
        
        return self.api_request(
            urls.endpoints["technical_data_bonds"].format(item_id, settlement),
            headers=headers
        )
    
    def get_historic_data(self, headers: dict[str,str], item_id: str, settlement: str, 
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
        if date_from != "":
            date_from = self._get_timestamp_string(date_from)
        if date_to != "":
            date_to = self._get_timestamp_string(date_to)
        return self.api_request(
            urls.endpoints["historic_data"].format(item_id, settlement, date_from, date_to),
            headers = headers
        )
    
    def get_intraday_data(self, headers: dict[str,str], item_id: str, settlement: str, 
                        ) -> dict[str, Any]:
        """Makes a request to the api to get the intraday data for an item

        Args:
            headers (dict[str,Any]): headers for the client that permits the request
            item_id (str). Example: "885981"
            settlement (str, optional): Settlement of instrument
        Returns:
            dict: Dict with the instrument intraday information
            
        """

        return self.api_request(
            urls.endpoints["intraday_data"].format(item_id, settlement),
            headers = headers
        )
        
    def api_request(
        self,
        path: str,
        headers:dict[str,str],
        retry: bool = True,
        method: str = "get",
        params: str = "",
        json_data: Dict[str, Any] = {},
        data: str = "",
    ):
        response = None
        
        if method not in ["get", "post", "delete"]:
            raise ApiException(f"Method {method} not suported")
        if method == "get":
            response = self.session.get(self._api_url(path), headers=headers)

        if method == "post":
            response = self.session.post(
                self._api_url(path),
                params=params,
                headers = headers,
                data=data,
                json=json_data,
            )

        if method == "delete":
            response = self.session.delete(
                self._api_url(path), json=json_data, headers=headers
            )
        if not response:
            raise ApiException("Bad HTTP API Response")

        json_response = simplejson.loads(response.text)
        
        if response.status_code == 401:
            if retry:
                self.api_request(path, retry=False)
            else:
                raise ApiException("Authentication Fails.")

        if response.status_code == 500:
            raise ApiException(f"Error 500 {json_response}")

        if response.status_code == 200:
            self._log_message(path, str(json_response))
        return json_response
    
    # def update_session_headers(self, header_update: Dict[str, Any]) -> None:
    #     self.session.headers.update(header_update)
        
    def _api_url(self, path: str) -> str:
        return urls.api_url + path
    
    def _log_message(self, url: str, message: str) -> None:
        msg: Dict[str, str] = {
            "url": url,
            # "timestamp": self._get_timestamp_string(),
            "message": message,
        }
        self.messages.append(msg)
        
    def _get_timestamp_string(self, input_string) -> str:
        """
        Args:
            input_string (str, optional): Start date. Format yyyy-MM-dd
        """
        input_date = datetime.strptime(input_string, "%Y-%m-%d")
        output_string = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")   
        return output_string