import pandas as pd
import logging
import os
from typing import List, Dict, Optional, Set
from src.services.notion_service import NotionClient

logger = logging.getLogger(__name__)

class ExporterService:
    def __init__(self, notion_client: NotionClient):
        self.notion = notion_client

    def export_all_to_csv(self, file_path: str) -> bool:
        """
        Exports all Notion database records to a CSV file.
        Includes resolving relations (Projects) if configured.
        """
        try:
            raw_records = self.notion.fetch_all_pages()

            # Resolve Projects/Trips if configured
            project_map = self._build_project_map(raw_records)

            rows = []
            for record in raw_records:
                rows.append(self._flatten_record(record, project_map))

            df = pd.DataFrame(rows)
            df.to_csv(file_path, index=False, sep=";", decimal=",")
            return True
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}", exc_info=True)
            return False

    def _build_project_map(self, records: List[Dict]) -> Dict[str, str]:
        """
        Builds a map of page_id -> title for related projects.
        """
        project_db_id = os.environ.get("NOTION_PROJECT_DATABASE_ID")
        if not project_db_id:
            return {}

        # Collect all project IDs from records
        needed_ids = set()
        for record in records:
            props = record.get("properties", {})
            # Assuming property name is "Proyecto/Viaje" as per original code
            # Note: Property names might vary, original code used "Proyecto/Viaje"
            # We check both relation and rollup

            # Check Relation
            relation = props.get("Proyecto/Viaje", {}).get("relation", [])
            for r in relation:
                needed_ids.add(r["id"])

            # Check Rollup (if it's a rollup of relation) - logic from original code
            rollup = props.get("Proyecto/Viaje", {}).get("rollup", {})
            if rollup.get("type") == "array":
                for item in rollup.get("array", []):
                    if item.get("type") == "relation":
                        if item.get("relation"):
                            needed_ids.add(item["relation"]["id"])

        if not needed_ids:
            return {}

        # Fetch all projects to build cache
        # Optimization: Fetch all projects from DB instead of one by one
        project_pages = self.notion.fetch_database_query(project_db_id)

        mapping = {}
        for p in project_pages:
            pid = p["id"]
            # Extract title
            props = p.get("properties", {})
            title = "Untitled"
            # Find the title property
            for key, val in props.items():
                if val["type"] == "title":
                    t_list = val["title"]
                    if t_list:
                        title = t_list[0].get("plain_text", "")
                    break

            if pid in needed_ids:
                mapping[pid] = title

        return mapping

    def export_categories_to_csv(self, file_path: str, category_db_id: str) -> bool:
        try:
            records = self.notion.fetch_database_query(category_db_id)
            rows = []
            for record in records:
                props = record.get("properties", {})

                # Subcategoria is title
                sub_title_list = props.get("Subcategoría", {}).get("title", [])
                subcategoria = sub_title_list[0].get("plain_text") if sub_title_list else ""

                # Categoria is select
                cat_select = props.get("Categoria", {}).get("select")
                categoria = cat_select.get("name") if cat_select else ""

                rows.append({
                    "subcategoria_id": record.get("id"),
                    "subcategoria": subcategoria,
                    "categoria": categoria
                })

            df = pd.DataFrame(rows)
            df.to_csv(file_path, index=False)
            return True
        except Exception as e:
            logger.error(f"Error exporting categories: {e}")
            return False

    def _flatten_record(self, record: Dict, project_map: Dict[str, str]) -> Dict:
        props = record.get("properties", {})

        def get_number(prop_name):
            return props.get(prop_name, {}).get("number")

        def get_select(prop_name):
            return props.get(prop_name, {}).get("select", {}).get("name")

        def get_date(prop_name):
            return props.get(prop_name, {}).get("date", {}).get("start")

        def get_title(prop_name):
            t = props.get(prop_name, {}).get("title", [])
            return t[0].get("plain_text") if t else None

        def get_relation_id(prop_name):
            r = props.get(prop_name, {}).get("relation", [])
            return r[0].get("id") if r else None

        def get_rollup_value(prop_name):
            # Try to extract plain text from rollup (array of text/select/etc)
            rollup = props.get(prop_name, {}).get("rollup", {})
            if rollup.get("type") == "array":
                array = rollup.get("array", [])
                if array:
                    first = array[0]
                    if first.get("type") == "select":
                        return first["select"]["name"]
                    if first.get("type") == "rich_text":
                        return first["rich_text"][0].get("plain_text") if first["rich_text"] else None
            return None

        # Resolve Project Names
        project_names = []
        # From relation
        relation = props.get("Proyecto/Viaje", {}).get("relation", [])
        for r in relation:
            name = project_map.get(r["id"])
            if name: project_names.append(name)

        # Original code also handled rollup for projects?
        # "If not proyecto_names and proyecto_prop type == rollup"
        if not project_names:
            rollup = props.get("Proyecto/Viaje", {}).get("rollup", {})
            if rollup.get("type") == "array":
                 for item in rollup.get("array", []):
                    if item.get("type") == "relation":
                        rid = item["relation"]["id"]
                        name = project_map.get(rid)
                        if name: project_names.append(name)

        project_str = ", ".join(project_names) if project_names else None

        return {
            "Nombre": get_title("Nombre"),
            "Fecha": get_date("Fecha"),
            "Cuenta": get_select("Cuenta"),
            "Gasto": get_number("Gasto"),
            "Ingreso": get_number("Ingreso"),
            "Transferencias": get_number("Transferencias"),
            "Subcategoría": get_relation_id("Subcategoría"),
            "Categoría": get_rollup_value("Categoría"),
            "Proyecto/Viaje": project_str,
            "Mes": props.get("Mes", {}).get("formula", {}).get("string"),
            "Script": props.get("Script", {}).get("checkbox"),
            "url": record.get("url"),
        }
