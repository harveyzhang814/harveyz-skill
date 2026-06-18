from __future__ import annotations
import requests


class SyncthingError(Exception):
    pass


class SyncthingClient:
    def __init__(self, api_url: str, api_key: str):
        self._base = api_url.rstrip("/")
        self._headers = {"X-API-Key": api_key}

    def _url(self, path: str) -> str:
        return f"{self._base}/{path.lstrip('/')}"

    def _check(self, resp: requests.Response) -> requests.Response:
        if resp.status_code >= 400:
            raise SyncthingError(f"HTTP {resp.status_code}: {resp.text}")
        return resp

    def ping(self) -> bool:
        try:
            r = requests.get(self._url("/rest/system/ping"), headers=self._headers, timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def get_folders(self) -> list[dict]:
        r = self._check(requests.get(self._url("/rest/config/folders"), headers=self._headers, timeout=10))
        return r.json()

    def add_folder(self, folder: dict) -> None:
        r = requests.post(self._url("/rest/config/folders"), headers=self._headers, json=folder, timeout=10)
        self._check(r)

    def remove_folder(self, folder_id: str) -> None:
        r = requests.delete(self._url(f"/rest/config/folders/{folder_id}"), headers=self._headers, timeout=10)
        self._check(r)

    def update_folder(self, folder_id: str, data: dict) -> None:
        r = requests.put(self._url(f"/rest/config/folders/{folder_id}"), headers=self._headers, json=data, timeout=10)
        self._check(r)

    def get_devices(self) -> list[dict]:
        r = self._check(requests.get(self._url("/rest/config/devices"), headers=self._headers, timeout=10))
        return r.json()

    def add_device(self, device: dict) -> None:
        r = requests.post(self._url("/rest/config/devices"), headers=self._headers, json=device, timeout=10)
        self._check(r)

    def remove_device(self, device_id: str) -> None:
        r = requests.delete(self._url(f"/rest/config/devices/{device_id}"), headers=self._headers, timeout=10)
        self._check(r)

    def get_connections(self) -> dict:
        r = self._check(requests.get(self._url("/rest/system/connections"), headers=self._headers, timeout=10))
        return r.json()

    def get_completion(self, folder_id: str) -> float:
        r = self._check(requests.get(
            self._url("/rest/db/completion"),
            headers=self._headers,
            params={"folder": folder_id},
            timeout=10,
        ))
        return r.json().get("completion", 0.0)

    def scan_folder(self, folder_id: str) -> None:
        r = requests.post(
            self._url("/rest/db/scan"),
            headers=self._headers,
            params={"folder": folder_id},
            timeout=10,
        )
        self._check(r)

    def get_my_device_id(self) -> str:
        r = self._check(requests.get(self._url("/rest/system/status"), headers=self._headers, timeout=10))
        return r.json()["myID"]

    def shutdown(self) -> None:
        r = requests.post(self._url("/rest/system/shutdown"), headers=self._headers, timeout=10)
        self._check(r)
