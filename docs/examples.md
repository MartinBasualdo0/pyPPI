# Ejemplos

## Autenticación con variable de entorno

```python
import os
from py_ppi_arg import PPI

app = PPI(
    user=os.environ["PPI_USER"],
    password=os.environ["PPI_PASSWORD"],
)
```

## Autenticación con 2FA automático (TOTP)

Si usás una app de autenticación (como Google Authenticator), podés usar `pyotp` para automatizar el flujo:

```python
import pyotp
from py_ppi_arg import PPI

totp = pyotp.TOTP(os.environ["PPI_OTP_SECRET"])

app = PPI(
    user=os.environ["PPI_USER"],
    password=os.environ["PPI_PASSWORD"],
    otp_provider=totp.now,
)
```

## Obtener todos los bonos soberanos en T2

```python
bonos = app.get_tickers_list(
    instrument_type=app.instrument_types.PUBLIC_BOND,
    operation_type=app.operation_types.COMPRA,
    settlement=app.settlements.T2,
)

for bono in bonos.get("items", []):
    print(bono["shortName"], bono["price"])
```

## Comparar precio CI vs T2 de un bono

```python
al30_ci = app.search_tickers(short_ticker="AL30D")  # dólar cable
al30_t2 = app.search_tickers(short_ticker="AL30")

precio_ci = al30_ci["price"]
precio_t2 = al30_t2["price"]
print(f"AL30 CI: {precio_ci} | AL30 T2: {precio_t2}")
```

## Calcular el dólar MEP implícito

```python
# AL30 en pesos (T2)
al30_pesos = app.search_tickers(short_ticker="AL30")
# AL30 en dólares (T2)
al30_usd = app.search_tickers(short_ticker="AL30D")

mep = al30_pesos["price"] / al30_usd["price"]
print(f"Dólar MEP implícito AL30: ${mep:.2f}")
```

## Datos históricos como DataFrame

```python
import pandas as pd

historico = app.get_historic_data(
    item_id="261",
    settlement=app.settlements.T2,
    date_from="2024-01-01",
    date_to="2024-12-31",
)

df = pd.DataFrame(historico["items"])
df["date"] = pd.to_datetime(df["date"])
df = df.set_index("date").sort_index()
print(df[["closePrice", "volume"]].head())
```

## Iterar todos los tipos de instrumentos

```python
tipos = [
    app.instrument_types.PUBLIC_BOND,
    app.instrument_types.CORPORATE,
    app.instrument_types.LETRAS,
]

for tipo in tipos:
    resultado = app.get_tickers_list(
        instrument_type=tipo,
        operation_type=app.operation_types.COMPRA,
        settlement=app.settlements.T2,
    )
    print(f"{tipo.name}: {len(resultado.get('items', []))} instrumentos")
```

## Manejo de errores

```python
from py_ppi_arg import PPI
from py_ppi_arg.components import ApiException

try:
    app = PPI(user="usuario@email.com", password="contraseña")
    data = app.get_historic_data(item_id="261", settlement=app.settlements.T2)
except ApiException as e:
    print(f"Error de API: {e}")
except Exception as e:
    print(f"Error inesperado: {e}")
```
