"""
User authentication and management system.
This module provides functionality for user registration, login, and session management.
"""

import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List

class User:
    """Represents a user in the system."""
    
    def __init__(self, username: str, email: str, password: str):
        self.id = str(uuid.uuid4())
        self.username = username
        self.email = email
        self.password_hash = self._hash_password(password)
        self.created_at = datetime.utcnow()
        self.last_login = None
        self.is_active = True
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the stored hash."""
        return self.password_hash == self._hash_password(password)
    
    def to_dict(self) -> Dict:
        """Convert user to dictionary representation."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active
        }

class UserManager:
    """Manages user operations and authentication."""
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, str] = {}  # session_id -> user_id
    
    def register_user(self, username: str, email: str, password: str) -> Optional[User]:
        """Register a new user."""
        if self._user_exists(username, email):
            return None
        
        user = User(username, email, password)
        self.users[user.id] = user
        return user
    
    def _user_exists(self, username: str, email: str) -> bool:
        """Check if a user with the given username or email already exists."""
        for user in self.users.values():
            if user.username == username or user.email == email:
                return True
        return False
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user by username and password."""
        for user in self.users.values():
            if user.username == username and user.check_password(password):
                user.last_login = datetime.utcnow()
                return user
        return None
    
    def create_session(self, user: User) -> str:
        """Create a new session for the user."""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = user.id
        return session_id
    
    def get_user_by_session(self, session_id: str) -> Optional[User]:
        """Get user by session ID."""
        user_id = self.sessions.get(session_id)
        if user_id:
            return self.users.get(user_id)
        return None
    
    def logout_user(self, session_id: str) -> bool:
        """Logout a user by removing their session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def get_all_users(self) -> List[User]:
        """Get all users in the system."""
        return list(self.users.values())
    
    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user account."""
        user = self.users.get(user_id)
        if user:
            user.is_active = False
            return True
        return False

# Global user manager instance
user_manager = UserManager()

def get_user_manager() -> UserManager:
    """Get the global user manager instance."""
    return user_manager
