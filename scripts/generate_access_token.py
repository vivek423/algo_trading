from kiteconnect import KiteConnect
from dotenv import load_dotenv
import os
import logging
from session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_and_save_access_token(manual_request_token=None):
    """Generate access token and save session"""
    session_manager = SessionManager()
    
    # Check if we already have a valid session
    if session_manager.get_kite_instance():
        logger.info("Already have a valid session!")
        return True

    # Load environment variables
    load_dotenv()
    api_key = os.getenv('API_KEY')
    api_secret = os.getenv('API_SECRET')
    request_token = manual_request_token or os.getenv('REQUEST_TOKEN')

    if not all([api_key, api_secret]):
        raise ValueError("Missing API_KEY or API_SECRET in .env file")

    if not request_token:
        raise ValueError("No request token provided. Please run get_request_token.py first.")

    try:
        # Initialize Kite Connect
        kite = KiteConnect(api_key=api_key)
        
        # Generate session and get access token
        data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = data["access_token"]
        
        # Save session
        session_manager.save_session(access_token)
        
        # Initialize kite with new token
        kite.set_access_token(access_token)
        
        # Validate token works
        if session_manager.validate_token():
            logger.info("Access token generated and validated successfully!")
            return True
        else:
            logger.error("Token validation failed after generation")
            return False

    except Exception as e:
        logger.error(f"Error generating access token: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        request_token = input("Please enter the request token (or press Enter to use token from .env): ").strip()
        success = generate_and_save_access_token(request_token if request_token else None)
        if not success:
            logger.error("Failed to generate or validate access token")
    except Exception as e:
        print(f"Error: {str(e)}") 