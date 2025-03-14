from trading_client import TradingClient
from data_validator import DataValidator
from data_persistence import DataPersistenceChecker
import pandas as pd
from datetime import datetime, timedelta
import os
import logging
from typing import List, Dict, Optional, Tuple, Union
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import backoff
import yaml
import pytz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataFetcher:
    def __init__(self, config_path: str = None, max_workers: int = 5, retry_attempts: int = 3):
        self.client = TradingClient()
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'inputs')
        self.max_workers = max_workers
        self.retry_attempts = retry_attempts
        self.validator = DataValidator()
        self.persistence = DataPersistenceChecker(self.data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load configuration
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'trading_config.yaml')
        self.config = self.load_config(config_path)
        
    def load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            raise

    def get_stock_list(self) -> List[Dict]:
        """Get list of stocks based on configuration"""
        if self.config['stocks'] == 'all':
            return self.get_all_equity_stocks()
        else:
            return self.get_specific_stocks(self.config['stocks'])

    def get_specific_stocks(self, symbols: List[str]) -> List[Dict]:
        """Get information for specific stock symbols"""
        try:
            instruments = self.client.get_instruments(exchange="NSE")
            if not instruments:
                raise ValueError("No instruments returned from the API")

            # Filter for specified symbols
            stock_info = []
            for instrument in instruments:
                if (instrument.get('tradingsymbol') in symbols and
                    instrument.get('segment') == self.config['asset_filters']['segment'] and
                    instrument.get('instrument_type') == self.config['asset_filters']['instrument_type'] and
                    instrument.get('exchange') == self.config['asset_filters']['exchange']):
                    stock_info.append(instrument)

            if not stock_info:
                raise ValueError("None of the specified symbols found in equity instruments")

            logger.info(f"Found {len(stock_info)} specified stocks")
            return stock_info

        except Exception as e:
            logger.error(f"Error fetching specific stocks: {str(e)}")
            raise

    def get_all_equity_stocks(self) -> List[Dict]:
        """Get all equity stocks based on filters"""
        try:
            instruments = self.client.get_instruments(exchange="NSE")
            if not instruments:
                raise ValueError("No instruments returned from the API")

            # Apply filters from config
            equity_instruments = [
                instrument for instrument in instruments
                if (
                    instrument.get('segment') == self.config['asset_filters']['segment'] and
                    instrument.get('instrument_type') == self.config['asset_filters']['instrument_type'] and
                    instrument.get('exchange') == self.config['asset_filters']['exchange'] and
                    not any(x in instrument.get('tradingsymbol', '')
                           for x in self.config['asset_filters']['exclude_symbols'])
                )
            ]

            logger.info(f"Found {len(equity_instruments)} equity instruments")
            
            # Sort by market cap and volume
            equity_instruments.sort(
                key=lambda x: (float(x.get('market_cap', 0)), float(x.get('average_daily_volume', 0))),
                reverse=True
            )
            
            # Take top 100 stocks
            stocks = equity_instruments[:100]
            logger.info(f"Selected top 100 stocks by market cap and volume")
            
            # Save the stock list
            stock_list_file = os.path.join(self.data_dir, 'selected_stocks.json')
            with open(stock_list_file, 'w') as f:
                json.dump(stocks, f, indent=2)
            
            return stocks

        except Exception as e:
            logger.error(f"Error fetching all equity stocks: {str(e)}")
            raise

    def verify_data_integrity(self):
        """Verify integrity of all downloaded data"""
        logger.info("Verifying data integrity...")
        results = self.persistence.verify_all_files()
        
        failed_files = [f for f, valid in results.items() if not valid]
        if failed_files:
            logger.error(f"Data integrity check failed for {len(failed_files)} files")
            return failed_files
        
        logger.info("All files passed integrity check")
        return []
        
    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def get_historical_data(self, symbol: str, exchange: str = "NSE", 
                          months: int = None, interval: str = None) -> Tuple[str, Optional[pd.DataFrame]]:
        """Get historical OHLC data for a given stock with retries"""
        try:
            # Use config values if not specified
            if months is None:
                months = self.config.get('months_of_history', 60)
            if interval is None:
                interval = self.config.get('interval', 'day')
                
            file_name = f"{symbol}_{interval}.csv"
            file_path = os.path.join(self.data_dir, file_name)
            
            # Get current time in India timezone
            ist = pytz.timezone('Asia/Kolkata')
            now = datetime.now(ist)
            
            # Initialize from_date as months ago
            from_date = (now - timedelta(days=30*months)).replace(tzinfo=None)
            existing_df = None
            
            # Check if we have existing data
            if os.path.exists(file_path) and self.persistence.verify_file_integrity(file_path):
                existing_df = pd.read_csv(file_path, index_col='timestamp', parse_dates=True)
                if not existing_df.empty:
                    # Get the latest timestamp from existing data
                    latest_timestamp = existing_df.index.max()
                    
                    # For daily data, handle current day differently
                    if interval == "day":
                        today = now.date()
                        if latest_timestamp.date() == today:
                            # During market hours, remove today's incomplete data
                            market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
                            market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
                            
                            if market_open <= now <= market_close:
                                # Remove today's incomplete data
                                existing_df = existing_df[existing_df.index.date < today]
                                logger.info(f"Removed incomplete data for today ({today}) for {symbol}")
                            elif now > market_close:
                                # After market hours, keep today's data
                                from_date = (latest_timestamp + timedelta(days=1)).replace(tzinfo=None)
                                logger.info(f"Market closed, keeping today's data for {symbol}")
                        else:
                            # Set from_date to the day after the last complete day
                            from_date = (latest_timestamp + timedelta(days=1)).replace(tzinfo=None)
                    
                    logger.info(f"Found existing data for {symbol}, last timestamp: {latest_timestamp}")
                    
                    # If we're up to date and it's not today or not market hours, return existing data
                    if from_date.date() > now.date():
                        logger.info(f"Data for {symbol} is already up to date")
                        return symbol, existing_df
            
            # Calculate to_date
            to_date = now.replace(tzinfo=None)
            
            # Add delay between requests to avoid rate limiting
            time.sleep(0.5)
            
            # Fetch new data
            logger.info(f"Fetching new data for {symbol} from {from_date} to {to_date}")
            new_data = self.client.get_historical_data(
                symbol=symbol,
                exchange=exchange,
                from_date=from_date,
                to_date=to_date,
                interval=interval
            )
            
            if not new_data:
                logger.info(f"No new data found for {symbol}")
                return symbol, existing_df
                
            # Convert new data to DataFrame
            new_df = pd.DataFrame(new_data)
            new_df['timestamp'] = pd.to_datetime(new_df['date']).dt.tz_localize(None)
            new_df.set_index('timestamp', inplace=True)
            new_df.drop('date', axis=1, inplace=True)
            
            # Validate and clean new data
            if not self.validator.validate_ohlc_data(new_df, symbol):
                logger.error(f"Data validation failed for new data of {symbol}")
                return symbol, existing_df
                
            new_df = self.validator.clean_ohlc_data(new_df)
            
            # Combine existing and new data if we have both
            if existing_df is not None and not existing_df.empty:
                # Remove any potential overlap to avoid duplicates
                new_df = new_df[~new_df.index.isin(existing_df.index)]
                if not new_df.empty:
                    df = pd.concat([existing_df, new_df])
                    df = df.sort_index()  # Sort by timestamp
                    logger.info(f"Added {len(new_df)} new records for {symbol}")
                else:
                    df = existing_df
                    logger.info(f"No new records to add for {symbol}")
            else:
                df = new_df
                logger.info(f"Created new dataset with {len(df)} records for {symbol}")
            
            # Save to file
            df.to_csv(file_path)
            
            # Save metadata
            self.persistence.save_metadata(file_path, df)
            
            return symbol, df
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return symbol, None

    def fetch_all_data(self):
        """Fetch historical data for all Nifty 100 stocks using parallel processing"""
        try:
            # Check authentication first
            if not self.client._ensure_connection():
                logger.error("""
Authentication failed! Please follow these steps:
1. Run: python scripts/get_request_token.py
2. Login to Zerodha in the browser window that opens
3. After successful login, the script will automatically save your tokens
4. Then run this script again
""")
                return

            # Clean up any stale metadata
            self.persistence.clean_missing_files()
            
            # Get Nifty 100 stocks
            stocks = self.get_stock_list()
            if not stocks:
                raise ValueError("Failed to get stock list")
            
            failed_symbols = []
            successful_symbols = []
            
            # Process stocks sequentially to avoid rate limits
            with tqdm(total=len(stocks), desc="Fetching data") as pbar:
                for stock in stocks:
                    try:
                        symbol = stock['tradingsymbol']
                        symbol, df = self.get_historical_data(symbol)
                        
                        if df is not None:
                            successful_symbols.append(symbol)
                        else:
                            failed_symbols.append(symbol)
                            
                        # Add delay between stocks
                        time.sleep(1)  # 1 second delay between stocks
                        
                    except Exception as e:
                        logger.error(f"Task failed for {symbol}: {str(e)}")
                        failed_symbols.append(symbol)
                    
                    pbar.update(1)
            
            # Verify data integrity
            failed_integrity = self.verify_data_integrity()
            if failed_integrity:
                failed_symbols.extend([os.path.basename(f).split('_')[0] 
                                    for f in failed_integrity])
            
            # Report results
            logger.info(f"\nData fetch complete:")
            logger.info(f"Successful: {len(successful_symbols)} stocks")
            logger.info(f"Failed: {len(failed_symbols)} stocks")
            
            if failed_symbols:
                logger.warning("Failed symbols:")
                for symbol in failed_symbols:
                    logger.warning(f"- {symbol}")
            
            return successful_symbols, failed_symbols
            
        except Exception as e:
            logger.error(f"Error in fetch_all_data: {str(e)}")
            raise
            
def main():
    # Allow config path to be specified as command line argument
    import argparse
    parser = argparse.ArgumentParser(description='Fetch historical stock data')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    args = parser.parse_args()

    fetcher = DataFetcher(config_path=args.config)
    fetcher.fetch_all_data()

if __name__ == "__main__":
    main() 