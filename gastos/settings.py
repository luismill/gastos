import os
from pathlib import Path
from dotenv import load_dotenv


# Cargar variables desde .env en la raíz del repo
PROJECT_ROOT = Path(__file__).resolve().parent.parent
dotenv_path = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path)

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
# Optional: database for categories (subcategorías)
CATEGORY_DATABASE_ID = os.environ.get("NOTION_CATEGORY_DATABASE_ID")
# Optional: database for projects / trips (relation lookup)
PROJECT_DATABASE_ID = os.environ.get("NOTION_PROJECT_DATABASE_ID")

NOTION_API_URL = "https://api.notion.com/v1/"
NOTION_VERSION = os.environ.get("NOTION_VERSION", "2025-09-03")

if not NOTION_TOKEN or not DATABASE_ID:
    # Keep import-time side effects minimal; raise clear error if used
    # The modules that import settings may catch this if desired.
    raise RuntimeError(
        "Missing NOTION_TOKEN or NOTION_DATABASE_ID environment variables."
    )

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}
