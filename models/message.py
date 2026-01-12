"""
Message model - Direct messages and conversations
"""

from datetime import datetime

class Message:
    """Message class for direct messaging."""
    
    def __init__(self, message_id=None, sender_id=None, receiver_id=None,
                 content=None, sent_at=None, read=False):
        self._message_id = message_id
        self._sender_id = sender_id
        self._receiver_id = receiver_id
        self._content = content
        self._sent_at = sent_at or datetime.now()
        self._read = read
    
    @property
    def message_id(self):
        return self._message_id
    
    @property
    def sender_id(self):
        return self._sender_id
    
    @property
    def receiver_id(self):
        return self._receiver_id
    
    @property
    def content(self):
        return self._content
    
    @content.setter
    def content(self, value):
        if len(value) > 2000:
            raise ValueError("Message cannot exceed 2000 characters")
        self._content = value
    
    @property
    def is_read(self):
        return self._read
    
    def mark_as_read(self):
        """Mark the message as read."""
        self._read = True
    
    def to_dict(self):
        """Convert message to dictionary."""
        return {
            'message_id': self._message_id,
            'sender_id': self._sender_id,
            'receiver_id': self._receiver_id,
            'content': self._content,
            'sent_at': str(self._sent_at),
            'read': self._read
        }


class Conversation:
    """Conversation class to group messages between two users."""
    
    def __init__(self, conversation_id=None, user1_id=None, user2_id=None):
        self._conversation_id = conversation_id
        self._user1_id = user1_id
        self._user2_id = user2_id
        self._messages = []
    
    @property
    def conversation_id(self):
        return self._conversation_id
    
    def add_message(self, message):
        """Add a message to the conversation."""
        self._messages.append(message)
    
    def get_messages(self, limit=50):
        """Get recent messages from the conversation."""
        return self._messages[-limit:]
    
    def get_unread_count(self, for_user_id):
        """Count unread messages for a specific user."""
        return sum(1 for msg in self._messages 
                   if msg.receiver_id == for_user_id and not msg.is_read)
