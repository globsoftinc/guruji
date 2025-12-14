from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app.config import Config


class GoogleMeetService:
    """Service for creating and managing Google Meet sessions via Calendar API."""
    
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
        self.service = build('calendar', 'v3', credentials=self.credentials)
    
    def create_meet_event(self, title: str, start_time: datetime, 
                          duration_minutes: int = 60, attendee_emails: list = None) -> dict:
        """
        Create a Google Calendar event with Google Meet.
        
        Returns:
            dict with 'event_id', 'meet_link', 'calendar_link'
        """
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        event = {
            'summary': title,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'Asia/Kathmandu'
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'Asia/Kathmandu'
            },
            'conferenceData': {
                'createRequest': {
                    'requestId': f'guruji-{datetime.utcnow().timestamp()}',
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }
        }
        
        if attendee_emails:
            event['attendees'] = [{'email': email} for email in attendee_emails]
        
        created_event = self.service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1,
            sendUpdates='all' if attendee_emails else 'none'
        ).execute()
        
        return {
            'event_id': created_event['id'],
            'meet_link': created_event.get('conferenceData', {}).get('entryPoints', [{}])[0].get('uri', ''),
            'calendar_link': created_event.get('htmlLink', '')
        }
    
    def update_meet_event(self, event_id: str, title: str = None, 
                          start_time: datetime = None, duration_minutes: int = None) -> dict:
        """Update an existing calendar event."""
        # First get the existing event
        event = self.service.events().get(calendarId='primary', eventId=event_id).execute()
        
        if title:
            event['summary'] = title
        
        if start_time:
            end_time = start_time + timedelta(minutes=duration_minutes or 60)
            event['start'] = {
                'dateTime': start_time.isoformat(),
                'timeZone': 'Asia/Kathmandu'
            }
            event['end'] = {
                'dateTime': end_time.isoformat(),
                'timeZone': 'Asia/Kathmandu'
            }
        
        updated_event = self.service.events().update(
            calendarId='primary',
            eventId=event_id,
            body=event
        ).execute()
        
        return {
            'event_id': updated_event['id'],
            'meet_link': updated_event.get('conferenceData', {}).get('entryPoints', [{}])[0].get('uri', ''),
            'calendar_link': updated_event.get('htmlLink', '')
        }
    
    def delete_meet_event(self, event_id: str) -> bool:
        """Delete a calendar event."""
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting event: {e}")
            return False
    
    def get_upcoming_events(self, max_results: int = 10) -> list:
        """Get upcoming calendar events."""
        now = datetime.utcnow().isoformat() + 'Z'
        
        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])
