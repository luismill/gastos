Gastos - Procesador y exportador a Notion

Requisitos
- Python 3.10+
- Paquetes: ver `requirements.txt`

Instalación
- Crear y activar un entorno virtual
  - Windows PowerShell: `python -m venv .venv && .venv\\Scripts\\Activate.ps1`
- Instalar dependencias: `pip install -r requirements.txt`

Configuración (variables de entorno)
- `NOTION_TOKEN`: token de integración de Notion (Bearer)
- `NOTION_DATABASE_ID`: ID de la base de datos principal de gastos
- `NOTION_CATEGORY_DATABASE_ID` (opcional): ID de la BD de subcategorías
- `NOTION_VERSION` (opcional): por defecto `2022-06-28`

Ejemplo en PowerShell:
```
$env:NOTION_TOKEN="secret_..."
$env:NOTION_DATABASE_ID="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
$env:NOTION_CATEGORY_DATABASE_ID="yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"
```

Alternativa: archivo .env
- Puedes usar un archivo `.env` en la raíz (ya incluido y gitignored):
  - Edita `.env` y rellena:
    - `NOTION_TOKEN=...`
    - `NOTION_DATABASE_ID=...`
    - `NOTION_CATEGORY_DATABASE_ID=...` (opcional)
- `gastos/settings.py` carga automáticamente ese `.env`.

Uso
- Ejecutar GUI: `python -m gastos.main` o `python gastos/main.py`
- Botones:
  - Seleccionar fichero: lee extractos de BBVA, Laboral Kutxa o Revolut y sube a Notion
  - Exportar Notion a CSV: descarga todos los registros a un CSV
  - Exportar subcategorías a CSV: descarga la lista de subcategorías y guarda como CSV

Notas
- Los secretos ya no se guardan en `gastos/config.py`. Usa variables de entorno. Hay un `gastos/config_example.py` sólo como referencia de campos.
- Los logs se guardan en `logs/gastos_app.log`.
