from session_manager import SessionManager
import logging
from functools import wraps
import time
from typing import Optional, Callable, List, Dict
from kiteconnect import KiteConnect
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def retry_on_token_expiry(max_retries: int = 1):
    """Decorator to retry API calls on token expiry"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            retries = 0
            while retries <= max_retries:
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    if "token expired" in str(e).lower() or "invalid token" in str(e).lower():
                        logger.warning(f"Token expired during operation (attempt {retries + 1}/{max_retries + 1})")
                        if retries < max_retries:
                            self._handle_token_expiry()
                            retries += 1
                            continue
                    logger.error(f"Operation failed: {str(e)}")
                    raise
            return None
        return wrapper
    return decorator

class TradingClient:
    def __init__(self):
        self.session_manager = SessionManager()
        self.kite: Optional[KiteConnect] = None
        
    def _ensure_connection(self) -> bool:
        """Ensure we have a valid connection"""
        self.kite = self.session_manager.get_kite_instance()
        if not self.kite:
            logger.error("No valid session. Please run authentication flow.")
            return False
        return True

    def _handle_token_expiry(self):
        """Handle token expiry by clearing session"""
        self.session_manager.handle_token_expiry()
        self.kite = None
        logger.info("Please re-run authentication flow to get new tokens")

    @retry_on_token_expiry()
    def get_instruments(self, exchange: str = "NSE") -> List[Dict]:
        """Get list of instruments"""
        if not self._ensure_connection():
            return []
        return self.kite.instruments(exchange=exchange)

    @retry_on_token_expiry()
    def get_historical_data(self, symbol: str, exchange: str,
                          from_date: datetime, to_date: datetime,
                          interval: str) -> List[Dict]:
        """Get historical OHLCV data for a symbol"""
        if not self._ensure_connection():
            return []
            
        try:
            # Get instrument token
            instruments = self.get_instruments(exchange)
            instrument = next((i for i in instruments if i['tradingsymbol'] == symbol), None)
            
            if not instrument:
                logger.error(f"Instrument not found: {symbol}")
                return []
                
            # Get historical data
            # Zerodha intervals: minute, 3minute, 5minute, 10minute, 15minute, 30minute, 60minute, day
            data = self.kite.historical_data(
                instrument_token=instrument['instrument_token'],
                from_date=from_date,
                to_date=to_date,
                interval=interval,
                continuous=False,  # Regular trading hours only
                oi=False  # We don't need open interest for stocks
            )
            
            if not data:
                logger.warning(f"No data returned for {symbol}")
                return []

            # Log data sample for verification
            if data:
                logger.debug(f"Sample data for {symbol}: {data[0]}")
                logger.info(f"Got {len(data)} candles for {symbol} from {from_date} to {to_date}")

            return data
            
        except Exception as e:
            logger.error(f"Error fetching historical data: {str(e)}")
            return []

    @retry_on_token_expiry()
    def get_margins(self):
        """Get account margins with retry on token expiry"""
        if not self._ensure_connection():
            return None
        return self.kite.margins()

    @retry_on_token_expiry()
    def get_positions(self):
        """Get current positions with retry on token expiry"""
        if not self._ensure_connection():
            return None
        return self.kite.positions()

    @retry_on_token_expiry()
    def place_order(self, tradingsymbol: str, exchange: str, transaction_type: str, 
                   quantity: int, product: str, order_type: str, price: Optional[float] = None):
        """Place an order with retry on token expiry"""
        if not self._ensure_connection():
            return None
            
        try:
            return self.kite.place_order(
                variety=self.kite.VARIETY_REGULAR,
                exchange=exchange,
                tradingsymbol=tradingsymbol,
                transaction_type=transaction_type,
                quantity=quantity,
                product=product,
                order_type=order_type,
                price=price
            )
        except Exception as e:
            logger.error(f"Order placement failed: {str(e)}")
            raise

def main():
    """Example usage of TradingClient"""
    client = TradingClient()
    
    try:
        # Get instruments
        instruments = client.get_instruments()
        logger.info(f"Found {len(instruments)} instruments")
        
        # Get margins
        margins = client.get_margins()
        if margins:
            logger.info(f"Account margins: {margins}")
        
        # Get positions
        positions = client.get_positions()
        if positions:
            logger.info(f"Current positions: {positions}")
            
    except Exception as e:
        logger.error(f"Trading operations failed: {str(e)}")

if __name__ == "__main__":
    main() 