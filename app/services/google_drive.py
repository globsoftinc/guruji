from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app.config import Config


class GoogleDriveService:
    """Service for accessing Google Drive recordings."""
    
    def __init__(self, tokens: dict):
        """Initialize with user's OAuth tokens."""
        self.credentials = Credentials(
            token=tokens.get('access_token'),
            refresh_token=tokens.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=Config.GOOGLE_CLIENT_ID,
            client_secret=Config.GOOGLE_CLIENT_SECRET,
            scopes=Config.GOOGLE_SCOPES
        )
        self.service = build('drive', 'v3', credentials=self.credentials)
    
    def list_meet_recordings(self, days_back: int = 30) -> list:
        """
        List Google Meet recordings from Drive.
        Meet recordings are stored in 'Meet Recordings' folder.
        """
        # Calculate the date range
        since_date = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + 'Z'
        
        # Search for video files in Meet Recordings folder
        query = (
            f"mimeType contains 'video/' and "
            f"createdTime > '{since_date}' and "
            f"name contains 'Meet'"
        )
        
        try:
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, mimeType, createdTime, size, webViewLink, thumbnailLink)',
                orderBy='createdTime desc',
                pageSize=50
            ).execute()
            
            return results.get('files', [])
        except Exception as e:
            print(f"Error listing recordings: {e}")
            return []
    
    def get_file_details(self, file_id: str) -> dict:
        """Get detailed information about a file."""
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields='id, name, mimeType, createdTime, size, webViewLink, thumbnailLink, videoMediaMetadata'
            ).execute()
            return file
        except Exception as e:
            print(f"Error getting file details: {e}")
            return None
    
    def create_shareable_link(self, file_id: str) -> str:
        """
        Make a file viewable by anyone with the link.
        Returns the shareable link.
        """
        try:
            # Create permission for anyone to view
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            self.service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
            
            # Get the web view link
            file = self.service.files().get(
                fileId=file_id,
                fields='webViewLink'
            ).execute()
            
            return file.get('webViewLink', '')
        except Exception as e:
            print(f"Error creating shareable link: {e}")
            return None
    
    def get_video_duration(self, file_id: str) -> int:
        """
        Get video duration in seconds.
        Note: This only works for files that have been processed by Google.
        """
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields='videoMediaMetadata'
            ).execute()
            
            metadata = file.get('videoMediaMetadata', {})
            duration_ms = metadata.get('durationMillis', 0)
            return int(duration_ms) // 1000
        except Exception as e:
            print(f"Error getting video duration: {e}")
            return 0
