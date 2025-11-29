from typing import Optional, List, Dict
import os
import requests
import logging
import time
from datetime import date
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from src.core.models import Transaction

logger = logging.getLogger(__name__)

class NotionClient:
    def __init__(self, token: Optional[str] = None, database_id: Optional[str] = None):
        self.token = token or os.environ.get("NOTION_TOKEN")
        self.database_id = database_id or os.environ.get("NOTION_DATABASE_ID")
        self.api_url = "https://api.notion.com/v1/"
        self.version = os.environ.get("NOTION_VERSION", "2022-06-28")

        if not self.token or not self.database_id:
            raise ValueError("Faltan credenciales de Notion (NOTION_TOKEN, NOTION_DATABASE_ID)")

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": self.version,
            "Content-Type": "application/json",
        }

        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def get_transactions_in_range(self, start_date: date, end_date: date) -> List[Transaction]:
        """
        Fetches transactions from Notion within the given date range.
        Optimized to avoid downloading the whole database.
        """
        query_url = f"{self.api_url}databases/{self.database_id}/query"

        # Filter payload
        payload = {
            "filter": {
                "and": [
                    {
                        "property": "Fecha",
                        "date": {
                            "on_or_after": start_date.isoformat()
                        }
                    },
                    {
                        "property": "Fecha",
                        "date": {
                            "on_or_before": end_date.isoformat()
                        }
                    }
                ]
            }
        }

        results = []
        has_more = True
        next_cursor = None

        while has_more:
            if next_cursor:
                payload["start_cursor"] = next_cursor

            response = self.session.post(query_url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()

            results.extend(data.get("results", []))
            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")

        transactions = []
        for page in results:
            t = self._map_page_to_transaction(page)
            if t:
                transactions.append(t)
        return transactions

    def _map_page_to_transaction(self, page: Dict) -> Optional[Transaction]:
        props = page.get("properties", {})

        # Extract Date
        date_prop = props.get("Fecha", {}).get("date")
        if not date_prop:
            return None
        tx_date_str = date_prop.get("start")
        tx_date = date.fromisoformat(tx_date_str)

        # Extract Account
        account_select = props.get("Cuenta", {}).get("select")
        account = account_select.get("name") if account_select else "Unknown"

        # Extract Name
        title_list = props.get("Nombre", {}).get("title", [])
        description = title_list[0].get("plain_text") if title_list else "Sin Nombre"

        # Extract Amount (Gasto or Ingreso)
        expense = props.get("Gasto", {}).get("number")
        income = props.get("Ingreso", {}).get("number")

        amount = 0.0
        if expense is not None:
            amount = -float(expense) # Store as negative
        elif income is not None:
            amount = float(income)

        return Transaction(
            date=tx_date,
            description=description,
            amount=amount,
            account=account
        )

    def fetch_all_pages(self) -> List[Dict]:
        """Fetches all pages from the database (for export)."""
        query_url = f"{self.api_url}databases/{self.database_id}/query"
        results = []
        has_more = True
        next_cursor = None

        while has_more:
            payload = {}
            if next_cursor:
                payload["start_cursor"] = next_cursor

            response = self.session.post(query_url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()

            results.extend(data.get("results", []))
            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")

        return results

    def fetch_database_query(self, database_id: str) -> List[Dict]:
        """Generic fetch for any database (e.g., categories, projects)."""
        query_url = f"{self.api_url}databases/{database_id}/query"
        results = []
        has_more = True
        next_cursor = None

        while has_more:
            payload = {}
            if next_cursor:
                payload["start_cursor"] = next_cursor

            response = self.session.post(query_url, headers=self.headers, json=payload)
            if response.status_code != 200:
                logger.error(f"Error fetching DB {database_id}: {response.text}")
                break

            data = response.json()
            results.extend(data.get("results", []))
            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")

        return results

    def get_page_title(self, page_id: str) -> Optional[str]:
        url = f"{self.api_url}pages/{page_id}"
        resp = self.session.get(url, headers=self.headers)
        if resp.status_code == 200:
            props = resp.json().get("properties", {})
            # This is specific logic to extract title from whatever property is title
            # Reusing logic from old script:
            for prop in props.values():
                if prop.get("type") == "title":
                    titles = prop.get("title", [])
                    if titles:
                        return titles[0].get("plain_text")
        return None

    def create_transaction(self, transaction: Transaction) -> bool:
        url = f"{self.api_url}pages"

        properties = {
            "Nombre": {"title": [{"text": {"content": transaction.description}}]},
            "Fecha": {"date": {"start": transaction.date.isoformat()}},
            "Cuenta": {"select": {"name": transaction.account}},
            "Script": {"checkbox": True},
        }

        if transaction.is_expense:
             properties["Gasto"] = {"number": transaction.abs_amount}
        else:
             properties["Ingreso"] = {"number": transaction.abs_amount}

        if transaction.subcategory:
             properties["Subcategoría"] = {"relation": [{"id": transaction.subcategory}]}

        data = {
            "parent": {"database_id": self.database_id},
            "properties": properties
        }

        try:
            response = self.session.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            return False
