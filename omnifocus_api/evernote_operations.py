"""Evernote integration for context management and task synchronization."""
import os
from typing import List, Optional, Dict, Tuple
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import json
from datetime import datetime
from evernote.api.client import EvernoteClient
from evernote.edam.type.ttypes import Note, Notebook, NoteAttributes, ResourceAttributes
from evernote.edam.error.ttypes import EDAMSystemException, EDAMUserException, EDAMNotFoundException
from evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback and store the auth code."""
    auth_code = None
    
    def do_GET(self):
        """Handle GET request with OAuth callback."""
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        
        if 'code' in params:
            OAuthCallbackHandler.auth_code = params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"Authorization successful! You can close this window.")
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"Authorization failed! Please try again.")

class EvernoteManager:
    def __init__(self):
        """Initialize Evernote client with OAuth2."""
        self.client_id = os.getenv('EVERNOTE_CLIENT_ID')
        self.client_secret = os.getenv('EVERNOTE_CLIENT_SECRET')
        if not self.client_id or not self.client_secret:
            raise ValueError("EVERNOTE_CLIENT_ID and EVERNOTE_CLIENT_SECRET must be set")
        
        self.sandbox = os.getenv('EVERNOTE_SANDBOX', 'true').lower() == 'true'
        self.client = None
        self.note_store = None
        self._current_context = None

    def get_auth_url(self) -> str:
        """Get OAuth2 authorization URL."""
        client = EvernoteClient(
            consumer_key=self.client_id,
            consumer_secret=self.client_secret,
            sandbox=self.sandbox
        )
        return client.get_authorize_url()

    def authenticate(self) -> bool:
        """Perform OAuth2 authentication flow."""
        try:
            server = HTTPServer(('localhost', 8080), OAuthCallbackHandler)
            auth_url = self.get_auth_url()
            webbrowser.open(auth_url)
            server.handle_request()
            auth_code = OAuthCallbackHandler.auth_code
            
            if not auth_code:
                print("Failed to get authorization code")
                return False
            
            self.client = EvernoteClient(
                consumer_key=self.client_id,
                consumer_secret=self.client_secret,
                sandbox=self.sandbox
            )
            self.client.get_access_token(auth_code)
            self.note_store = self.client.get_note_store()
            return True
            
        except Exception as e:
            print(f"Authentication failed: {str(e)}")
            return False

    def ensure_authenticated(self) -> bool:
        """Ensure we have an authenticated client."""
        if not self.note_store:
            return self.authenticate()
        return True

    def link_task_note(self, task_id: str, note_id: str) -> bool:
        """Link a task to a note by adding metadata."""
        try:
            if not self.ensure_authenticated():
                return False

            note = self.note_store.getNote(note_id, True, False, False, False)
            attributes = note.attributes or NoteAttributes()
            
            # Store task link in note attributes
            if not hasattr(attributes, 'sourceURL'):
                attributes.sourceURL = ''
            attributes.sourceURL = f"omnifocus:///task/{task_id}"
            
            note.attributes = attributes
            self.note_store.updateNote(note)
            return True

        except Exception as e:
            print(f"Failed to link task and note: {str(e)}")
            return False

    def get_linked_notes(self, task_id: str) -> List[Dict]:
        """Get all notes linked to a specific task."""
        try:
            if not self.ensure_authenticated():
                return []

            note_filter = NoteFilter(
                words=f'sourceURL:omnifocus:///task/{task_id}'
            )
            spec = NotesMetadataResultSpec(
                includeTitle=True,
                includeAttributes=True,
                includeNotebookGuid=True
            )
            
            notes = self.note_store.findNotesMetadata(note_filter, 0, 100, spec)
            return [
                {
                    'id': n.guid,
                    'title': n.title,
                    'notebook_guid': n.notebookGuid,
                    'updated': n.updated
                }
                for n in notes.notes
            ]

        except Exception as e:
            print(f"Failed to get linked notes: {str(e)}")
            return []

    def get_current_context(self) -> Optional[Dict]:
        """Get information about the current context."""
        return self._current_context

    def switch_context(self, context_id: str) -> bool:
        """Switch to a specific context (note or notebook)."""
        try:
            if not self.ensure_authenticated():
                return False

            # Try to get as note first
            try:
                note = self.note_store.getNote(context_id, True, False, False, False)
                self._current_context = {
                    'type': 'note',
                    'id': note.guid,
                    'title': note.title,
                    'notebook_guid': note.notebookGuid
                }
                return True
            except EDAMNotFoundException:
                pass

            # Try as notebook
            try:
                notebook = self.note_store.getNotebook(context_id)
                self._current_context = {
                    'type': 'notebook',
                    'id': notebook.guid,
                    'name': notebook.name
                }
                return True
            except EDAMNotFoundException:
                print(f"Context {context_id} not found")
                return False

        except Exception as e:
            print(f"Failed to switch context: {str(e)}")
            return False

    def suggest_context(self) -> Optional[Dict]:
        """Suggest next context based on recent activity and time."""
        try:
            if not self.ensure_authenticated():
                return None

            # Get recently modified notes
            note_filter = NoteFilter(
                order=1,  # Most recently updated first
                ascending=False
            )
            spec = NotesMetadataResultSpec(
                includeTitle=True,
                includeAttributes=True,
                includeNotebookGuid=True
            )
            
            recent_notes = self.note_store.findNotesMetadata(note_filter, 0, 10, spec)
            if not recent_notes.notes:
                return None

            # Return most relevant note as suggested context
            suggested = recent_notes.notes[0]
            return {
                'type': 'note',
                'id': suggested.guid,
                'title': suggested.title,
                'notebook_guid': suggested.notebookGuid
            }

        except Exception as e:
            print(f"Failed to suggest context: {str(e)}")
            return None

    def create_note_for_task(self, task_id: str, title: str, content: str = "") -> Optional[str]:
        """Create a new note for task context."""
        try:
            if not self.ensure_authenticated():
                return None

            # Format content as ENML
            content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">
<en-note>
<h1>{title}</h1>
{content}
</en-note>'''

            note = Note()
            note.title = title
            note.content = content
            
            # Add task link
            attributes = NoteAttributes()
            attributes.sourceURL = f"omnifocus:///task/{task_id}"
            note.attributes = attributes

            created_note = self.note_store.createNote(note)
            return created_note.guid

        except Exception as e:
            print(f"Failed to create note: {str(e)}")
            return None

def test_evernote_export() -> bool:
    """Test Evernote integration by creating a test note."""
    try:
        manager = EvernoteManager()
        return manager.create_note(
            title="Test Note",
            content="<div><p>Test note from OmniFocus CLI</p></div>",
            notebook_name="Test"
        )
    except Exception as e:
        print(f"Failed to test Evernote integration: {str(e)}")
        return False

def export_to_evernote(title: str, content: str, notebook: str = "Reference Material", tags: List[str] = None) -> bool:
    """Export content to Evernote using the official SDK."""
    try:
        manager = EvernoteManager()
        return manager.create_note(
            title=title,
            content=content,
            notebook_name=notebook,
            tags=tags
        )
    except Exception as e:
        print(f"Failed to export to Evernote: {str(e)}")
        return False 