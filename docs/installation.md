# Instalación

## Requisitos

- Python 3.8 o superior
- Una cuenta activa en [Portfolio Personal](https://portfoliopersonal.com/)

## Instalación con pip

```bash
pip install py_ppi_arg
```

## Instalación desde el código fuente

```bash
git clone https://github.com/MartinBasualdo0/pyPPI.git
cd pyPPI
pip install -e .
```

## Dependencias

La librería instala automáticamente las siguientes dependencias:

| Paquete | Versión mínima | Uso |
|---------|----------------|-----|
| `requests` | 2.31.0 | HTTP client |
| `simplejson` | 3.19.1 | Parsing de respuestas JSON |
| `pyotp` | 2.9.0 | Soporte de 2FA |
| `cloudscraper` | 1.2.71 | Manejo de protecciones antibot |
| `beautifulsoup4` | 4.12.3 | Extracción de headers dinámicos |
