# Inicio rápido

## 1. Instalar e inicializar

```bash
pip install py_ppi_arg
```

```python
from py_ppi_arg import PPI

app = PPI(user="tu@email.com", password="tu_contraseña")
```

## 2. Listar instrumentos disponibles

Obtené la lista de bonos soberanos negociables a 48hs (T2):

```python
bonos = app.get_tickers_list(
    instrument_type=app.instrument_types.PUBLIC_BOND,
    operation_type=app.operation_types.COMPRA,
    settlement=app.settlements.T2,
)
```

Para obligaciones negociables o letras, cambiá `instrument_type`:

```python
# Obligaciones negociables
on = app.get_tickers_list(
    instrument_type=app.instrument_types.CORPORATE,
    operation_type=app.operation_types.COMPRA,
    settlement=app.settlements.T2,
)

# Letras
letras = app.get_tickers_list(
    instrument_type=app.instrument_types.LETRAS,
    operation_type=app.operation_types.COMPRA,
    settlement=app.settlements.T1,
)
```

## 3. Buscar un instrumento

Buscá por ticker corto o por ID interno:

```python
# Por ticker
al30 = app.search_tickers(short_ticker="AL30")

# Por ID interno
instrumento = app.search_tickers(item_id="885981")
```

## 4. Datos técnicos de un bono

Obtené TIR, duración, paridad y otros datos analíticos:

```python
tecnico = app.get_technical_data_bonds(
    settlement=app.settlements.T2,
    item_id="804421",
)
```

## 5. Datos históricos

```python
historico = app.get_historic_data(
    item_id="261",
    settlement=app.settlements.T2,
    date_from="2024-01-01",
    date_to="2024-12-31",
)
```

Omitiendo las fechas, devuelve todo el historial disponible:

```python
historico_completo = app.get_historic_data(
    item_id="261",
    settlement=app.settlements.T2,
)
```

## 6. Datos intradía

```python
intraday = app.get_intraday_data(
    item_id="261",
    settlement=app.settlements.T2,
)
```

## Tipos de liquidación (Settlement)

| Valor | Descripción |
|-------|-------------|
| `app.settlements.T0` | Contado inmediato (CI) |
| `app.settlements.T1` | 24 horas |
| `app.settlements.T2` | 48 horas |
| `app.settlements.T3` | 72 horas |
