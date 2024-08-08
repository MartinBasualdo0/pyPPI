# Welcome to py_ppi_arg' Documentation

## Overview

py_ppi_arg is a Python library that enables interaction with PortfolioPersonal REST APIs. It is designed to save developers hours of research and coding required to connect to PortfolioPersonal REST APIs.

## Disclaimer

py_ppi_arg is not owned by Cocos Capital, and the authors are not responsible for the use of this library.

## Installation

To install  py_ppi_arg, you can use the following command:

```
pip install py_ppi_arg
```

## API Credentials

To use this library, you need to have the correct authentication credentials.

## Dependencies

The library has the following dependency:

```
requests>=2.31.0
simplejson>=3.19.1
pyotp>=2.9.0
beautifulsoup4==4.12.3
bs4==0.0.2
```

## Features

#### Available Methods

#### Initialization

Before using the library, you need to initialize it with a valid email and password.

#### REST

The library provides functions to make requests to the REST API and retrieve the corresponding responses.

###### Functions

* **get_tickers_list**: Retrieves instruments quote list information filtered by instrument type, operation type and settlement.
* **search_tickers** : Queries the API to search for a particular instrument based on the name.
* **get_technical_data_bonds**: Retrieves the techical data for a bond.
* **get_historic_data**: Retrieves the historic data for an item.
* **get_intraday_data**: Retrieves the intraday data for an item.

> All functions return a dictionary representing the JSON response.

#### Enumerations

The library also provides enumerations to help developers avoid errors and improve readability.

* **Currency** : Identifies the available currencies in the app.
* **InstrumentTypes** : Identifies the instrument types.
* **OperationType**: Identifies the operation types.
* **Settlements** : Identifies the different settlement dates.

## Usage

Once the library has been installed, you can import and initialize it. The initialization sets the email and password. It then attempts to authenticate with the provided credentials. If the authentication fails, an `ApiException` is thrown.

```
from pycocos import Cocos

app = PPI(email="sample@email.com", password="S4mp13.p4ssW0rd")
```

#### REST

```
# Get information about all the available bonds
app.get_tickers_list(
    instrument_type = app.instrument_types.PUBLIC_BOND,
    operation_type = app.operation_types.COMPRA,
    settlement = app.settlements.T2
)

# Get the technical data for a bond
app.get_technical_data_bonds(
        settlement=app.settlements.T2,
        item_id="804421"
        )

# Get the historic price data for an instrument
app.get_historic_data(item_id="261", settlement=app.settlements.T2)

# Get the information about for an instrument
app.search_tickers(short_ticker = "AL30")

```

For more information you can check this [article.](https://medium.com/@nachoherrera/biblioteca-pycocos-a3579721c79e)

## Official API Documentation

There is no official API documentation for this library. The library was created by webscraping the app.

## Acknowledgements

This library was created taking as an example the work of the Scrappers Argentinos and Inversiones y Algoritmos Telegram Groups in the [pyCocos ](https://pypi.org/project/pyCocos/)library.

@LucaGelmini and @patruccoluciano helped by giving feedback and suggestions for a better code. Special thanks to them.
