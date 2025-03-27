from kiteconnect import KiteConnect
from dotenv import load_dotenv
import os
import time
import json
from datetime import datetime, timedelta
import logging
from typing import Optional, Dict
from setup_logging import setup_script_logging

# Configure logging
logger = setup_script_logging()

class SessionManager:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('API_KEY')
        self.api_secret = os.getenv('API_SECRET')
        self.session_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'session.json')
        self.kite: Optional[KiteConnect] = None
        
    def load_session(self) -> Dict:
        """Load session data from file if it exists and is valid"""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    session_data = json.load(f)
                    
                # Check if session is still valid (not expired)
                if self._is_session_valid(session_data):
                    return session_data
                else:
                    logger.info("Stored session has expired")
            return {}
        except Exception as e:
            logger.error(f"Error loading session: {str(e)}")
            return {}

    def save_session(self, access_token: str):
        """Save session data to file"""
        try:
            session_data = {
                'access_token': access_token,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=1)).isoformat()
            }
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f)
            logger.info("Session saved successfully")
        except Exception as e:
            logger.error(f"Error saving session: {str(e)}")

    def _is_session_valid(self, session_data: Dict) -> bool:
        """Check if the session is still valid"""
        try:
            expires_at = datetime.fromisoformat(session_data.get('expires_at', ''))
            return datetime.now() < expires_at
        except Exception:
            return False

    def initialize_kite(self) -> Optional[KiteConnect]:
        """Initialize KiteConnect with existing session or create new one"""
        try:
            if not self.api_key:
                raise ValueError("API_KEY not found in environment variables")

            # Create new KiteConnect instance
            self.kite = KiteConnect(api_key=self.api_key)

            # Try to load existing session
            session_data = self.load_session()
            if session_data and 'access_token' in session_data:
                self.kite.set_access_token(session_data['access_token'])
                logger.info("Loaded existing session")
                return self.kite

            # If no valid session exists, need to get new access token
            logger.info("No valid session found. Need to authenticate.")
            return None

        except Exception as e:
            logger.error(f"Error initializing Kite: {str(e)}")
            return None

    def validate_token(self) -> bool:
        """Validate if the current token is working"""
        try:
            if not self.kite:
                return False
            # Try to make a simple API call
            self.kite.margins()
            return True
        except Exception as e:
            logger.error(f"Token validation failed: {str(e)}")
            return False

    def handle_token_expiry(self):
        """Handle token expiry by clearing session"""
        try:
            if os.path.exists(self.session_file):
                os.remove(self.session_file)
            logger.info("Session cleared due to token expiry")
        except Exception as e:
            logger.error(f"Error handling token expiry: {str(e)}")

    def get_kite_instance(self) -> Optional[KiteConnect]:
        """Get a valid KiteConnect instance, handling token expiry"""
        if not self.kite:
            self.kite = self.initialize_kite()
            
        if self.kite and not self.validate_token():
            logger.info("Token validation failed, clearing session...")
            self.handle_token_expiry()
            self.kite = None
            
        return self.kite 