from typing import List, Dict, Optional
import sqlite3
import os
import datetime
import subprocess
from dataclasses import dataclass
from omnifocus_api.data_models import OmniFocusTask

@dataclass
class Message:
    id: str
    text: str
    date: datetime.datetime
    is_from_me: bool
    handle_id: str
    chat_id: str
    contact_name: Optional[str] = None  # Added contact name field

def check_messages_permissions() -> bool:
    """Check if we have permission to access the Messages database."""
    db_path = get_imessage_db_path()
    
    if not os.path.exists(db_path):
        print("Messages database not found. Make sure Messages.app is set up on this Mac.")
        return False
        
    # Try to read permissions
    try:
        # First check if Terminal has Full Disk Access
        process = subprocess.run(
            ["sqlite3", db_path, "SELECT COUNT(*) FROM sqlite_master;"],
            capture_output=True,
            text=True
        )
        
        if process.returncode == 0:
            return True
            
        print("\nPermission denied accessing Messages database.")
        print("\nTo fix this, you need to:")
        print("1. Open System Settings")
        print("2. Go to Privacy & Security > Full Disk Access")
        print("3. Click the '+' button")
        print("4. Navigate to /Applications/Utilities/")
        print("5. Select 'Terminal.app' (or your terminal app)")
        print("6. Restart your terminal")
        
        return False
        
    except Exception as e:
        print(f"\nError checking Messages permissions: {str(e)}")
        print("Please ensure Terminal.app has Full Disk Access in System Settings.")
        return False

def get_imessage_db_path() -> str:
    """Get the path to the iMessage database."""
    home = os.path.expanduser("~")
    return f"{home}/Library/Messages/chat.db"

def fetch_messages_for_contact(contact_name: str, days_back: int = 30) -> List[Message]:
    """
    Fetch recent messages from a specific contact.
    """
    if not check_messages_permissions():
        raise PermissionError("Cannot access Messages database. Please grant Full Disk Access to Terminal.app")

    # Calculate the cutoff date
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_back)
    unix_cutoff = int(cutoff_date.timestamp())

    # Connect to the database
    # Note: We make a copy to avoid locking the live database
    conn = sqlite3.connect(f"file:{get_imessage_db_path()}?mode=ro", uri=True)
    cursor = conn.cursor()

    try:
        # Query to get messages from the specified contact
        query = """
        SELECT 
            m.rowid,
            m.text,
            datetime(m.date/1000000000 + strftime('%s', '2001-01-01'), 'unixepoch', 'localtime'),
            m.is_from_me,
            m.handle_id,
            c.chat_identifier
        FROM message m
        JOIN chat_message_join cmj ON m.rowid = cmj.message_id
        JOIN chat c ON cmj.chat_id = c.rowid
        JOIN handle h ON m.handle_id = h.rowid
        WHERE (h.id LIKE ? OR c.display_name LIKE ?)
        AND m.date/1000000000 + strftime('%s', '2001-01-01') > ?
        ORDER BY m.date DESC
        """
        
        # Try different variations of the contact name/number
        patterns = [
            (f"%{contact_name}%", f"%{contact_name}%"),  # Name anywhere
            (f"{contact_name}@%", f"%{contact_name}%"),  # Email-style
            (f"+%{contact_name}", f"%{contact_name}%"),  # International phone
            (contact_name, contact_name),                # Exact match
        ]
        
        messages = []
        for handle_pattern, name_pattern in patterns:
            cursor.execute(query, (handle_pattern, name_pattern, unix_cutoff))
            rows = cursor.fetchall()
            if rows:
                for row in rows:
                    messages.append(Message(
                        id=str(row[0]),
                        text=row[1] if row[1] else "",
                        date=datetime.datetime.strptime(row[2], '%Y-%m-%d %H:%M:%S'),
                        is_from_me=bool(row[3]),
                        handle_id=str(row[4]),
                        chat_id=str(row[5])
                    ))
                break  # Stop if we found messages with this pattern
                
        return messages

    finally:
        conn.close()

def extract_action_items(messages: List[Message]) -> List[Dict[str, str]]:
    """
    Extract potential action items from messages.
    Returns a list of dictionaries with task details.
    """
    action_items = []
    
    # Keywords that might indicate action items
    action_keywords = [
        "can you", "could you", "please", "need to", "should", "will you",
        "let's", "lets", "follow up", "following up", "reminder", "don't forget",
        "todo", "to-do", "action item", "deadline", "by tomorrow", "by next",
        "meeting", "call", "discuss", "review", "send", "prepare", "schedule"
    ]
    
    for msg in messages:
        text = msg.text.lower()
        
        # Skip if message is too short or empty
        if not text or len(text) < 10:
            continue
            
        # Check for action keywords
        if any(keyword in text for keyword in action_keywords):
            # Create task title from first line or first X characters
            title = msg.text.split('\n')[0][:100]
            
            action_items.append({
                'title': title,
                'note': f"From iMessage conversation on {msg.date.strftime('%Y-%m-%d %H:%M')}\n\nFull message:\n{msg.text}",
                'due_date': None,  # Could be extracted with NLP if needed
                'message_id': msg.id,
                'date': msg.date.strftime('%Y-%m-%d %H:%M:%S'),
                'is_from_me': msg.is_from_me
            })
    
    return action_items

def sync_messages_to_tasks(contact_name: str, project_name: str = None) -> List[Dict[str, str]]:
    """
    Sync recent messages from a contact to OmniFocus tasks.
    Returns a list of extracted action items.
    """
    try:
        # Fetch recent messages
        messages = fetch_messages_for_contact(contact_name)
        
        if not messages:
            return []
        
        # Extract action items
        action_items = extract_action_items(messages)
        
        return action_items
        
    except Exception as e:
        print(f"Error syncing messages: {str(e)}")
        return []

def fetch_recent_messages(days_back: int = 7) -> List[Message]:
    """
    Fetch all recent messages across all conversations.
    """
    if not check_messages_permissions():
        raise PermissionError("Cannot access Messages database. Please grant Full Disk Access to Terminal.app")

    # Calculate the cutoff date
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_back)
    unix_cutoff = int(cutoff_date.timestamp())

    # Connect to the database
    conn = sqlite3.connect(f"file:{get_imessage_db_path()}?mode=ro", uri=True)
    cursor = conn.cursor()

    try:
        # Query to get recent messages with contact info
        query = """
        SELECT 
            m.rowid,
            m.text,
            datetime(m.date/1000000000 + strftime('%s', '2001-01-01'), 'unixepoch', 'localtime'),
            m.is_from_me,
            m.handle_id,
            c.chat_identifier,
            COALESCE(c.display_name, h.id) as contact_name
        FROM message m
        JOIN chat_message_join cmj ON m.rowid = cmj.message_id
        JOIN chat c ON cmj.chat_id = c.rowid
        JOIN handle h ON m.handle_id = h.rowid
        WHERE m.date/1000000000 + strftime('%s', '2001-01-01') > ?
        ORDER BY m.date DESC
        """
        
        cursor.execute(query, (unix_cutoff,))
        rows = cursor.fetchall()
        
        messages = []
        for row in rows:
            messages.append(Message(
                id=str(row[0]),
                text=row[1] if row[1] else "",
                date=datetime.datetime.strptime(row[2], '%Y-%m-%d %H:%M:%S'),
                is_from_me=bool(row[3]),
                handle_id=str(row[4]),
                chat_id=str(row[5]),
                contact_name=str(row[6])
            ))
                
        return messages

    finally:
        conn.close()

def scan_recent_action_items(days_back: int = 7) -> List[Dict[str, str]]:
    """
    Scan recent messages across all conversations for action items.
    Returns a list of potential action items with contact information.
    """
    try:
        # Fetch recent messages
        messages = fetch_recent_messages(days_back)
        
        if not messages:
            return []
        
        # Extract action items
        action_items = []
        for msg in messages:
            text = msg.text.lower()
            
            # Skip if message is too short or empty
            if not text or len(text) < 10:
                continue
                
            # Check for action keywords
            if any(keyword in text for keyword in action_keywords):
                # Create task title from first line or first X characters
                title = msg.text.split('\n')[0][:100]
                
                action_items.append({
                    'title': title,
                    'note': f"From iMessage conversation with {msg.contact_name} on {msg.date.strftime('%Y-%m-%d %H:%M')}\n\nFull message:\n{msg.text}",
                    'due_date': None,
                    'message_id': msg.id,
                    'date': msg.date.strftime('%Y-%m-%d %H:%M:%S'),
                    'is_from_me': msg.is_from_me,
                    'contact': msg.contact_name
                })
        
        return action_items
        
    except Exception as e:
        print(f"Error scanning messages: {str(e)}")
        return []

# List of keywords that might indicate action items
action_keywords = [
    "can you", "could you", "please", "need to", "should", "will you",
    "let's", "lets", "follow up", "following up", "reminder", "don't forget",
    "todo", "to-do", "action item", "deadline", "by tomorrow", "by next",
    "meeting", "call", "discuss", "review", "send", "prepare", "schedule",
    "confirm", "check", "update", "sync", "coordinate", "plan", "organize",
    "decide", "determine", "investigate", "research", "look into", "find out",
    "get back", "circle back", "loop back", "touch base", "reconnect",
    "draft", "write", "create", "make", "build", "develop", "implement",
    "due by", "needed by", "required by", "must have", "important",
    "urgent", "asap", "priority", "critical", "key", "essential"
] 