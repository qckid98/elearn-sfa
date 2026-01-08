"""
Google Drive Service
Handles folder creation and file uploads to Google Drive using OAuth 2.0
"""
import os
import re
import logging
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from googleapiclient.errors import HttpError
import io

logger = logging.getLogger(__name__)

class GoogleDriveError(Exception):
    """Custom exception for Google Drive operations"""
    pass

class GoogleDriveService:
    """Service class for Google Drive operations using OAuth"""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    TOKEN_URI = 'https://oauth2.googleapis.com/token'
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    
    def __init__(self):
        self.credentials = None
        self.service = None
        self.root_folder_id = os.environ.get('GOOGLE_DRIVE_ROOT_FOLDER_ID')
        self._initialized = False
        self._initialize()
    
    def _initialize(self):
        """Initialize Google Drive API client using OAuth refresh token"""
        client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
        client_secret = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
        refresh_token = os.environ.get('GOOGLE_OAUTH_REFRESH_TOKEN')
        
        if not all([client_id, client_secret, refresh_token]):
            logger.warning("Google Drive credentials not configured. Set GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_OAUTH_REFRESH_TOKEN")
            return
        
        try:
            self.credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri=self.TOKEN_URI,
                client_id=client_id,
                client_secret=client_secret,
                scopes=self.SCOPES
            )
            self.service = build('drive', 'v3', credentials=self.credentials)
            self._initialized = True
            logger.info("Google Drive service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service: {e}")
            self.service = None
    
    @property
    def is_configured(self):
        """Check if the service is properly configured and ready to use"""
        return self._initialized and self.service is not None
    
    def _sanitize_folder_name(self, name):
        """Sanitize folder name to prevent issues with special characters"""
        if not name:
            return "Unnamed"
        # Remove or replace problematic characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip(' .')
        # Limit length
        return sanitized[:100] if len(sanitized) > 100 else sanitized
    
    def _execute_with_retry(self, request, operation_name="API call"):
        """Execute a Google API request with retry logic"""
        last_error = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                return request.execute()
            except HttpError as e:
                last_error = e
                if e.resp.status in [403, 429, 500, 502, 503, 504]:
                    # Retryable errors
                    wait_time = self.RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"{operation_name} failed (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    # Non-retryable error
                    raise GoogleDriveError(f"{operation_name} failed: {e}")
            except Exception as e:
                last_error = e
                logger.error(f"{operation_name} unexpected error: {e}")
                raise GoogleDriveError(f"{operation_name} failed: {e}")
        
        raise GoogleDriveError(f"{operation_name} failed after {self.MAX_RETRIES} retries: {last_error}")
    
    def create_folder(self, name, parent_folder_id=None):
        """
        Create a folder in Google Drive
        Returns: folder_id
        """
        if not self.is_configured:
            raise GoogleDriveError("Google Drive service not configured")
        
        safe_name = self._sanitize_folder_name(name)
        parent = parent_folder_id or self.root_folder_id
        
        if not parent:
            raise GoogleDriveError("No parent folder specified and GOOGLE_DRIVE_ROOT_FOLDER_ID not set")
        
        file_metadata = {
            'name': safe_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent]
        }
        
        request = self.service.files().create(
            body=file_metadata,
            fields='id, name',
            supportsAllDrives=True
        )
        
        folder = self._execute_with_retry(request, f"Create folder '{safe_name}'")
        logger.info(f"Created folder: {safe_name} (ID: {folder.get('id')})")
        
        return folder.get('id')
    
    def find_folder(self, name, parent_folder_id):
        """
        Find a folder by name in parent folder
        Returns: folder_id or None
        """
        if not self.is_configured:
            return None
        
        safe_name = self._sanitize_folder_name(name)
        # Escape single quotes in folder name for query
        escaped_name = safe_name.replace("'", "\\'")
        
        query = f"name='{escaped_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_folder_id}' in parents and trashed=false"
        
        request = self.service.files().list(
            q=query,
            fields='files(id, name)',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        )
        
        results = self._execute_with_retry(request, f"Find folder '{safe_name}'")
        files = results.get('files', [])
        
        return files[0]['id'] if files else None
    
    def find_or_create_folder(self, name, parent_folder_id):
        """
        Find existing folder by name in parent, or create if not exists
        Returns: folder_id
        """
        if not self.is_configured:
            raise GoogleDriveError("Google Drive service not configured")
        
        existing_id = self.find_folder(name, parent_folder_id)
        if existing_id:
            logger.debug(f"Found existing folder: {name} (ID: {existing_id})")
            return existing_id
        
        return self.create_folder(name, parent_folder_id)
    
    def create_student_folders(self, student_name, enrollments):
        """
        Create folder structure for a student:
        /StudentName/ProgramName/ClassName
        
        Uses find_or_create to prevent duplicate folders on re-runs.
        
        Args:
            student_name: Name of the student
            enrollments: List of enrollment objects with program and class_enrollments
            
        Returns:
            dict with folder IDs: {
                'student_folder_id': str,
                'class_folders': {class_enrollment_id: folder_id}
            }
            
        Raises:
            GoogleDriveError: If folder creation fails
        """
        if not self.is_configured:
            raise GoogleDriveError("Google Drive service not configured")
        
        if not self.root_folder_id:
            raise GoogleDriveError("GOOGLE_DRIVE_ROOT_FOLDER_ID not set")
        
        result = {'student_folder_id': None, 'class_folders': {}}
        
        # Find or create student root folder
        student_folder_id = self.find_or_create_folder(student_name, self.root_folder_id)
        result['student_folder_id'] = student_folder_id
        
        for enrollment in enrollments:
            # Find or create program folder
            program_name = enrollment.program.name
            program_folder_id = self.find_or_create_folder(program_name, student_folder_id)
            
            # Find or create class folders
            for ce in enrollment.class_enrollments:
                class_name = ce.program_class.name
                class_folder_id = self.find_or_create_folder(class_name, program_folder_id)
                result['class_folders'][ce.id] = class_folder_id
        
        logger.info(f"Student folders ready for {student_name}: {len(result['class_folders'])} class folders")
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
            
        Raises:
            GoogleDriveError: If upload fails
        """
        if not self.is_configured:
            raise GoogleDriveError("Google Drive service not configured")
        
        safe_filename = self._sanitize_folder_name(filename)
        
        file_metadata = {
            'name': safe_filename,
            'parents': [folder_id]
        }
        
        # Handle bytes or file-like object
        if isinstance(file_stream, bytes):
            file_stream = io.BytesIO(file_stream)
        
        media = MediaIoBaseUpload(file_stream, mimetype=mimetype, resumable=True)
        
        request = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink',
            supportsAllDrives=True
        )
        
        file = self._execute_with_retry(request, f"Upload file '{safe_filename}'")
        
        logger.info(f"Uploaded file: {safe_filename} (ID: {file.get('id')})")
        
        return {
            'id': file.get('id'),
            'url': file.get('webViewLink')
        }
    
    def get_folder_url(self, folder_id):
        """Get the URL to view a folder in Google Drive"""
        if not folder_id:
            return None
        return f"https://drive.google.com/drive/folders/{folder_id}"
    
    def delete_file(self, file_id):
        """Delete a file from Google Drive"""
        if not self.is_configured:
            raise GoogleDriveError("Google Drive service not configured")
        
        if not file_id:
            raise GoogleDriveError("No file ID provided")
        
        request = self.service.files().delete(fileId=file_id, supportsAllDrives=True)
        self._execute_with_retry(request, f"Delete file {file_id}")
        logger.info(f"Deleted file: {file_id}")
    
    def check_folder_exists(self, folder_id):
        """Check if a folder exists and is accessible"""
        if not self.is_configured:
            return False
        
        try:
            request = self.service.files().get(
                fileId=folder_id,
                fields='id, name, trashed',
                supportsAllDrives=True
            )
            result = self._execute_with_retry(request, f"Check folder {folder_id}")
            return not result.get('trashed', False)
        except GoogleDriveError:
            return False


# Singleton instance
_drive_service = None

def get_drive_service():
    """Get or create the Google Drive service instance"""
    global _drive_service
    if _drive_service is None:
        _drive_service = GoogleDriveService()
    return _drive_service

def reset_drive_service():
    """Reset the singleton instance (useful for testing or credential refresh)"""
    global _drive_service
    _drive_service = None

