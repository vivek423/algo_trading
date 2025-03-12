from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import webbrowser
import os
import threading
import signal
import sys
from kiteconnect import KiteConnect
import time
from session_manager import SessionManager

# Global variables
request_token = None
server_instance = None
server_thread = None

# Constants
PORT = 8989
REDIRECT_URL = f"http://localhost:{PORT}"

class RequestTokenHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global request_token, server_instance
        # Parse the URL and query parameters
        query_components = parse_qs(urlparse(self.path).query)
        
        # Extract request token
        if 'request_token' in query_components:
            request_token = query_components['request_token'][0]
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            response = """
            <html>
            <body>
                <h1>Authorization Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
                <script>window.close();</script>
            </body>
            </html>
            """
            self.wfile.write(response.encode())
            
            try:
                # Load API credentials
                env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
                load_dotenv(env_path)
                api_key = os.getenv('API_KEY')
                api_secret = os.getenv('API_SECRET')

                if not all([api_key, api_secret]):
                    raise ValueError("Missing API credentials in .env file")

                # Generate access token immediately
                kite = KiteConnect(api_key=api_key)
                data = kite.generate_session(request_token, api_secret=api_secret)
                access_token = data["access_token"]

                # Save session using SessionManager
                session_manager = SessionManager()
                session_manager.save_session(access_token)

                # Read existing .env content
                env_content = []
                if os.path.exists(env_path):
                    with open(env_path, 'r') as file:
                        env_content = file.readlines()

                # Update or add tokens
                updates = {
                    'REQUEST_TOKEN': request_token,
                    'ACCESS_TOKEN': access_token
                }

                for key, value in updates.items():
                    token_line = f"{key}={value}\n"
                    token_found = False
                    
                    for i, line in enumerate(env_content):
                        if line.startswith(f"{key}="):
                            env_content[i] = token_line
                            token_found = True
                            break
                    
                    if not token_found:
                        env_content.append(token_line)

                # Write back to .env
                with open(env_path, 'w') as file:
                    file.writelines(env_content)

                print("\nAuthorization successful!")
                print(f"Request Token: {request_token}")
                print(f"Access Token: {access_token}")
                print("Tokens have been saved to .env file")

                # Validate the access token
                kite.set_access_token(access_token)
                profile = kite.profile()  # Simple API call to validate token
                print(f"Successfully authenticated as: {profile['user_name']}")

            except Exception as e:
                print(f"\nError during token generation: {str(e)}")
            
            finally:
                # Schedule server shutdown in a new thread
                threading.Thread(target=self.shutdown_server, daemon=True).start()

    def shutdown_server(self):
        """Shutdown the server after a brief delay"""
        global server_instance
        time.sleep(1)  # Give time for the response to be sent
        if server_instance:
            server_instance.shutdown()
            server_instance.server_close()
            print("\nServer shutdown complete. You can close this terminal.")
            os._exit(0)  # Force exit after successful token generation

    def log_message(self, format, *args):
        """Suppress logging of HTTP requests"""
        return

def signal_handler(signum, frame):
    """Handle interrupt signals"""
    print("\nReceived interrupt signal. Shutting down...")
    if server_instance:
        server_instance.shutdown()
        server_instance.server_close()
    sys.exit(0)

def get_request_token():
    global server_instance, server_thread
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    
    # Load environment variables
    load_dotenv()
    api_key = os.getenv('API_KEY')

    if not api_key:
        raise ValueError("API_KEY not found in .env file")

    try:
        # Initialize Kite
        kite = KiteConnect(api_key=api_key)
        
        # Start local server
        server_instance = HTTPServer(('localhost', PORT), RequestTokenHandler)
        server_thread = threading.Thread(target=server_instance.serve_forever, daemon=True)
        server_thread.start()

        # Construct and open the Zerodha login URL
        login_url = f"https://kite.trade/connect/login?api_key={api_key}&v=3"
        print("\nOpening Zerodha login page in your browser...")
        print("Please login and authorize the application.")
        print(f"After login, you will be redirected to {REDIRECT_URL}")
        webbrowser.open(login_url)

        # Wait for server thread (with timeout)
        max_wait_time = 300  # 5 minutes timeout
        start_time = time.time()
        while server_thread.is_alive() and time.time() - start_time < max_wait_time:
            time.sleep(1)
            if request_token:  # If we got the token, we can break early
                break

        if time.time() - start_time >= max_wait_time:
            print("\nTimeout waiting for authorization. Please try again.")
            signal_handler(None, None)
        
        return request_token

    except Exception as e:
        print(f"\nError: {str(e)}")
        if server_instance:
            server_instance.shutdown()
            server_instance.server_close()
        return None

if __name__ == "__main__":
    get_request_token() 