import io
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
_KML_MIME = "application/vnd.google-earth.kml+xml"


class DriveClient:
    def __init__(self, credentials_path: str | None = None, folder_id: str | None = None):
        if credentials_path is None:
            credentials_path = os.environ["GOOGLE_DRIVE_CREDENTIALS_JSON"]
        self._folder_id = folder_id or os.environ.get("TRAVEL_MAPS_FOLDER_ID")
        creds = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=_SCOPES
        )
        self._service = build("drive", "v3", credentials=creds, cache_discovery=False)

    def upload_kml(self, filename: str, kml_content: str) -> str:
        """Upload a new KML file. Returns the Drive file ID."""
        metadata = {"name": filename, "mimeType": _KML_MIME}
        if self._folder_id:
            metadata["parents"] = [self._folder_id]

        media = MediaIoBaseUpload(
            io.BytesIO(kml_content.encode("utf-8")),
            mimetype=_KML_MIME,
            resumable=False,
        )
        file = (
            self._service.files()
            .create(body=metadata, media_body=media, fields="id")
            .execute()
        )
        file_id = file["id"]
        self._make_public(file_id)
        return file_id

    def update_kml(self, file_id: str, kml_content: str) -> None:
        """Overwrite the content of an existing Drive KML file."""
        media = MediaIoBaseUpload(
            io.BytesIO(kml_content.encode("utf-8")),
            mimetype=_KML_MIME,
            resumable=False,
        )
        self._service.files().update(fileId=file_id, media_body=media).execute()

    def _make_public(self, file_id: str) -> None:
        self._service.permissions().create(
            fileId=file_id,
            body={"role": "reader", "type": "anyone"},
        ).execute()

    @staticmethod
    def map_url(file_id: str) -> str:
        encoded = f"https://drive.google.com/uc?export=download&id={file_id}"
        import urllib.parse
        return f"https://www.google.com/maps?q={urllib.parse.quote(encoded, safe='')}"
