from dotenv import load_dotenv
import os
from kiteconnect import KiteConnect
from generate_access_token import generate_and_save_access_token

# Load environment variables
load_dotenv()

api_key = os.getenv('API_KEY')
access_token = os.getenv('ACCESS_TOKEN')

if not all([api_key, access_token]):
    print("Access token not found. Attempting to generate new access token...")
    try:
        access_token = generate_and_save_access_token()
    except Exception as e:
        raise ValueError(f"Failed to generate access token: {str(e)}")

# Initialize Kite Connect with access token
kite = KiteConnect(api_key=api_key)
kite.set_access_token(access_token)

# Now you can use kite for making API calls
# ... rest of your code ...