import requests

class SyncService:
    def __init__(self, backend_url: str = ""):
        self.backend_url = backend_url

    def sync_session(self, session_data: dict) -> bool:
        if not self.backend_url:
            return False
        try:
            response = requests.post(f"{self.backend_url}/api/sync", json=session_data, timeout=5)
            return response.status_code == 200
        except Exception:
            return False
