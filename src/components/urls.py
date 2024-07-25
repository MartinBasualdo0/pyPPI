# -*- coding: utf-8 -*-
"""
pyPPI.urls
Defines all API Paths
"""

api_url = "https://api.portfoliopersonal.com/"
account_url = 'https://cuenta.portfoliopersonal.com'

endpoints = {
    "token": "api/Seguridad/Auth/Login",
    "cuenta_ID": "/api/Cuenta/ComitentesAsignados",
    "refresh_token": "/api/Seguridad/Auth/RefreshToken",
    "ticker_search": "/api/Cotizaciones/Item/Search?q={}", #short ticker or id
    "ranking": "/api/Cotify/Ranking",
    "bonds_groups":"/api/Cotizaciones/Bono/PorGrupo?id=13463",
    "tickers_list": "/api/Ordenes/InstrumentosOperables?cuentaID={}&tipoProducto={}&tipoOperacion={}&tipoPlazoLiquidacion={}",
    "technical_data_bonds": "/api/Cotizaciones/Bono/{}/DatosTecnicos?plazoLiquidacionID={}",
    "historic_data":"/api/Cotizaciones/Item/{}/Historico/{}?fechaDesde={}&fechaHasta={}",
    "intraday_data":"/api/Cotizaciones/Item/{}/Intradiario?idPlazo={}"
}

