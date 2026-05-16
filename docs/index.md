# py_ppi_arg

**py_ppi_arg** es un conector Python para las REST APIs de [Portfolio Personal (PPI)](https://portfoliopersonal.com/), la plataforma argentina de inversiones. Permite obtener datos de mercado, cotizaciones, datos históricos e intradía de bonos e instrumentos financieros sin necesidad de investigar la API internamente.

```bash
pip install py_ppi_arg
```

## Ejemplo rápido

```python
from py_ppi_arg import PPI

app = PPI(user="tu@email.com", password="tu_contraseña")

# Listar bonos soberanos disponibles
bonos = app.get_tickers_list(
    instrument_type=app.instrument_types.PUBLIC_BOND,
    operation_type=app.operation_types.COMPRA,
    settlement=app.settlements.T2,
)

# Buscar un bono por ticker
al30 = app.search_tickers(short_ticker="AL30")

# Datos históricos
historico = app.get_historic_data(
    item_id="261",
    settlement=app.settlements.T2,
    date_from="2024-01-01",
    date_to="2024-12-31",
)
```

## Características

- Autenticación con soporte de **doble factor (2FA)**
- Listado y búsqueda de instrumentos financieros
- Datos técnicos de bonos (TIR, duración, paridad)
- Datos históricos e intradía por instrumento
- Enumeraciones para evitar errores en parámetros
- Manejo de errores con excepciones descriptivas

## Instrumentos soportados

| Tipo | Enum |
|------|------|
| Bonos soberanos | `InstrumentType.PUBLIC_BOND` |
| Obligaciones negociables | `InstrumentType.CORPORATE` |
| Letras | `InstrumentType.LETRAS` |

## Disclaimer

py_ppi_arg no es propiedad de Portfolio Personal. Los autores no se responsabilizan por el uso que se haga de esta librería. Utilizala bajo tu propia responsabilidad y respetá los términos de uso de la plataforma.
