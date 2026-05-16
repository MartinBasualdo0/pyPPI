# Referencia de API

## Clase `PPI`

Punto de entrada principal de la librería. Al instanciarla, autentica automáticamente con la API de PPI.

```python
from py_ppi_arg import PPI

app = PPI(user, password, otp_provider=None, remember_device=False)
```

### Constructor

| Parámetro | Tipo | Requerido | Default | Descripción |
|-----------|------|-----------|---------|-------------|
| `user` | `str` | Sí | — | Email de la cuenta PPI |
| `password` | `str` | Sí | — | Contraseña de la cuenta |
| `otp_provider` | `Callable[[], str]` | No | `None` | Función sin argumentos que retorna el código 2FA |
| `remember_device` | `bool` | No | `False` | Recordar el dispositivo para saltear 2FA futuro |

**Lanza:** `ApiException` si la autenticación falla.

---

## Métodos

### `get_tickers_list`

Retorna la lista de instrumentos cotizables filtrada por tipo, operación y plazo de liquidación.

```python
app.get_tickers_list(instrument_type, operation_type, settlement) -> dict
```

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `instrument_type` | `InstrumentType` | Tipo de instrumento |
| `operation_type` | `OperationType` | Tipo de operación |
| `settlement` | `Settlement` | Plazo de liquidación |

**Retorna:** `dict` con la lista de instrumentos y sus cotizaciones.

```python
bonos = app.get_tickers_list(
    instrument_type=app.instrument_types.PUBLIC_BOND,
    operation_type=app.operation_types.COMPRA,
    settlement=app.settlements.T2,
)
```

---

### `search_tickers`

Busca un instrumento por ticker corto o por ID interno. Usá uno u otro, no ambos.

```python
app.search_tickers(short_ticker=None, item_id=None) -> dict
```

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `short_ticker` | `str` | Ticker corto del instrumento. Ej: `"AL30"`, `"DNC3"` |
| `item_id` | `str` | ID interno del instrumento. Ej: `"885981"` |

**Retorna:** `dict` con la información del instrumento.

```python
# Por ticker
al30 = app.search_tickers(short_ticker="AL30")

# Por ID
instrumento = app.search_tickers(item_id="885981")
```

---

### `get_technical_data_bonds`

Retorna datos técnicos de un bono: TIR, duración, paridad, precio, y otros indicadores analíticos.

```python
app.get_technical_data_bonds(settlement, item_id) -> dict
```

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `settlement` | `Settlement` | Plazo de liquidación |
| `item_id` | `str` | ID interno del bono |

**Retorna:** `dict` con los datos técnicos.

```python
tecnico = app.get_technical_data_bonds(
    settlement=app.settlements.T2,
    item_id="804421",
)
```

---

### `get_historic_data`

Retorna los datos históricos de precios para un instrumento.

```python
app.get_historic_data(item_id, settlement, date_from="", date_to="") -> dict
```

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `item_id` | `str` | ID interno del instrumento |
| `settlement` | `Settlement` | Plazo de liquidación |
| `date_from` | `str` | Fecha inicio. Formato `yyyy-MM-dd`. Opcional. |
| `date_to` | `str` | Fecha fin. Formato `yyyy-MM-dd`. Opcional. |

**Retorna:** `dict` con el historial de precios.

```python
historico = app.get_historic_data(
    item_id="261",
    settlement=app.settlements.T2,
    date_from="2024-01-01",
    date_to="2024-12-31",
)
```

---

### `get_intraday_data`

Retorna los datos intradía (precios tick a tick durante la sesión actual) para un instrumento.

```python
app.get_intraday_data(item_id, settlement) -> dict
```

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `item_id` | `str` | ID interno del instrumento |
| `settlement` | `Settlement` | Plazo de liquidación |

**Retorna:** `dict` con los datos intradía.

```python
intraday = app.get_intraday_data(
    item_id="261",
    settlement=app.settlements.T2,
)
```

---

## Enumeraciones

Accesibles como atributos de la instancia para mayor comodidad (`app.instrument_types`, etc.) o importando directamente desde el módulo.

### `InstrumentType`

```python
from py_ppi_arg.components import InstrumentType
```

| Valor | Descripción |
|-------|-------------|
| `InstrumentType.PUBLIC_BOND` | Bonos soberanos / públicos |
| `InstrumentType.CORPORATE` | Obligaciones negociables (corporativas) |
| `InstrumentType.LETRAS` | Letras del tesoro |

### `Settlement`

```python
from py_ppi_arg.components import Settlement
```

| Valor | Descripción |
|-------|-------------|
| `Settlement.T0` | Contado inmediato (CI) |
| `Settlement.T1` | Liquidación a 24hs |
| `Settlement.T2` | Liquidación a 48hs |
| `Settlement.T3` | Liquidación a 72hs |

### `OperationType`

```python
from py_ppi_arg.components import OperationType
```

| Valor | Descripción |
|-------|-------------|
| `OperationType.COMPRA` | Compra |
| `OperationType.OTRO` | Otro tipo de operación |

---

## Excepciones

### `ApiException`

Lanzada ante errores de autenticación, respuestas HTTP no exitosas, o problemas al parsear la respuesta.

```python
from py_ppi_arg import PPI
from py_ppi_arg.components import ApiException

try:
    app = PPI(user="usuario@email.com", password="contraseña_incorrecta")
except ApiException as e:
    print(f"Error: {e}")
```
