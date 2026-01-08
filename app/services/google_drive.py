"""
Google Drive Service
Handles folder creation and file uploads to Google Drive using OAuth 2.0
"""
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
import io

class GoogleDriveService:
    """Service class for Google Drive operations using OAuth"""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    TOKEN_URI = 'https://oauth2.googleapis.com/token'
    
    def __init__(self):
        self.credentials = None
        self.service = None
        self.root_folder_id = os.environ.get('GOOGLE_DRIVE_ROOT_FOLDER_ID')
        self._initialize()
    
    def _initialize(self):
        """Initialize Google Drive API client using OAuth refresh token"""
        client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
        client_secret = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
        refresh_token = os.environ.get('GOOGLE_OAUTH_REFRESH_TOKEN')
        
        if client_id and client_secret and refresh_token:
            self.credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri=self.TOKEN_URI,
                client_id=client_id,
                client_secret=client_secret,
                scopes=self.SCOPES
            )
            self.service = build('drive', 'v3', credentials=self.credentials)
    
    def create_folder(self, name, parent_folder_id=None):
        """
        Create a folder in Google Drive
        Returns: folder_id
        """
        if not self.service:
            raise Exception("Google Drive service not initialized")
        
        parent = parent_folder_id or self.root_folder_id
        
        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent] if parent else []
        }
        
        folder = self.service.files().create(
            body=file_metadata,
            fields='id',
            supportsAllDrives=True
        ).execute()
        
        return folder.get('id')
    
    def find_or_create_folder(self, name, parent_folder_id):
        """
        Find existing folder by name in parent, or create if not exists
        Returns: folder_id
        """
        if not self.service:
            raise Exception("Google Drive service not initialized")
        
        # Search for existing folder
        query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and '{parent_folder_id}' in parents and trashed=false"
        
        results = self.service.files().list(
            q=query,
            fields='files(id, name)',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        files = results.get('files', [])
        
        if files:
            # Return existing folder
            return files[0]['id']
        else:
            # Create new folder
            return self.create_folder(name, parent_folder_id)
    
    def create_student_folders(self, student_name, enrollments):
        """
        Create folder structure for a student:
        /StudentName/ProgramName/ClassName
        
        Args:
            student_name: Name of the student
            enrollments: List of enrollment objects with program and class_enrollments
            
        Returns:
            dict with folder IDs: {
                'student_folder_id': str,
                'class_folders': {class_enrollment_id: folder_id}
            }
        """
        result = {'student_folder_id': None, 'class_folders': {}}
        
        # Create student root folder
        student_folder_id = self.create_folder(student_name)
        result['student_folder_id'] = student_folder_id
        
        for enrollment in enrollments:
            # Create program folder
            program_name = enrollment.program.name
            program_folder_id = self.create_folder(program_name, student_folder_id)
            
            # Create class folders
            for ce in enrollment.class_enrollments:
                class_name = ce.program_class.name
                class_folder_id = self.create_folder(class_name, program_folder_id)
                result['class_folders'][ce.id] = class_folder_id
        
        return result
    
    def upload_file(self, file_stream, filename, folder_id, mimetype='application/octet-stream'):
        """
        Upload a file to Google Drive
        
        Args:
            file_stream: File-like object or bytes
            filename: Name for the file
            folder_id: ID of target folder
            mimetype: MIME type of the file
            
        Returns:
            dict with file info: {'id': file_id, 'url': web_view_url}
        """
        if not self.service:
            raise Exception("Google Drive service not initialized")
        
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        
        # Handle bytes or file-like object
        if isinstance(file_stream, bytes):
            file_stream = io.BytesIO(file_stream)
        
        media = MediaIoBaseUpload(file_stream, mimetype=mimetype, resumable=True)
        
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink',
            supportsAllDrives=True
        ).execute()
        
        return {
            'id': file.get('id'),
            'url': file.get('webViewLink')
        }
    
    def get_folder_url(self, folder_id):
        """Get the URL to view a folder in Google Drive"""
        return f"https://drive.google.com/drive/folders/{folder_id}"
    
    def delete_file(self, file_id):
        """Delete a file from Google Drive"""
        if not self.service:
            raise Exception("Google Drive service not initialized")
        
        self.service.files().delete(fileId=file_id, supportsAllDrives=True).execute()


# Singleton instance
_drive_service = None

def get_drive_service():
    """Get or create the Google Drive service instance"""
    global _drive_service
    if _drive_service is None:
        _drive_service = GoogleDriveService()
    return _drive_service
