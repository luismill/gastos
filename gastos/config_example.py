NOTION_TOKEN = "notion_token"
DATABASE_ID = "database_id"
CATEGORY_DATABASE_ID = "category_database_id"
PROJECT_DATABASE_ID = "project_database_id"
NOTION_VERSION = "2025-09-03"
NOTION_API_URL = "https://api.notion.com/v1/"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json"
}
