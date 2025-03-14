import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger(__name__)

class DataValidator:
    @staticmethod
    def validate_ohlc_data(df: pd.DataFrame, symbol: str) -> bool:
        """Validate OHLC data for common issues"""
        if df is None or df.empty:
            logger.error(f"{symbol}: Empty dataset")
            return False

        try:
            # Check for missing values
            if df.isnull().any().any():
                logger.error(f"{symbol}: Contains missing values")
                return False

            # Check price consistency
            invalid_prices = (
                (df['high'] < df['low']) |
                (df['open'] < df['low']) |
                (df['close'] < df['low']) |
                (df['open'] > df['high']) |
                (df['close'] > df['high'])
            )
            
            if invalid_prices.any():
                logger.error(f"{symbol}: Invalid price relationships found")
                return False

            # Check for zero prices
            if (df[['open', 'high', 'low', 'close']] == 0).any().any():
                logger.error(f"{symbol}: Zero prices found")
                return False

            # Check for reasonable price changes
            pct_change = df['close'].pct_change().abs()
            if (pct_change > 0.2).any():  # 20% price change threshold
                logger.warning(f"{symbol}: Large price changes detected")

            # Check time continuity (for daily data)
            time_diff = df.index.to_series().diff()
            expected_diff = pd.Timedelta(days=1)
            
            # Get market days (excluding weekends)
            is_weekday = df.index.dayofweek < 5
            weekday_diffs = time_diff[is_weekday].dropna()
            
            if not all(td == expected_diff for td in weekday_diffs):
                logger.warning(f"{symbol}: Non-continuous timestamps detected in trading days")

            # Check volume
            if 'volume' in df.columns:
                if (df['volume'] <= 0).any():
                    logger.error(f"{symbol}: Invalid volume values found")
                    return False

            # Special check for current day's data
            today = pd.Timestamp.now(tz='Asia/Kolkata').date()
            if df.index.max().date() == today:
                market_end = pd.Timestamp.now(tz='Asia/Kolkata').replace(hour=15, minute=30)
                if pd.Timestamp.now(tz='Asia/Kolkata') < market_end:
                    logger.info(f"{symbol}: Contains incomplete current day data")

            return True

        except Exception as e:
            logger.error(f"{symbol}: Validation error - {str(e)}")
            return False

    @staticmethod
    def clean_ohlc_data(df: pd.DataFrame) -> pd.DataFrame:
        """Clean OHLC data by handling common issues"""
        if df is None or df.empty:
            return df

        # Remove duplicates
        df = df[~df.index.duplicated(keep='first')]

        # Sort by timestamp
        df = df.sort_index()

        # Forward fill missing values (up to 2 periods)
        df = df.fillna(method='ffill', limit=2)

        # Remove remaining rows with missing values
        df = df.dropna()

        return df

    @staticmethod
    def validate_stock_list(stocks: List[Dict]) -> List[Dict]:
        """Validate stock list data"""
        valid_stocks = []
        
        for stock in stocks:
            try:
                # Check for minimum required fields
                if not stock.get('tradingsymbol'):
                    logger.warning(f"Missing trading symbol in stock data")
                    continue

                # Basic validation of trading symbol
                symbol = stock['tradingsymbol']
                if not symbol or len(symbol) < 2:
                    logger.warning(f"Invalid trading symbol: {symbol}")
                    continue

                # Ensure we have either instrument token or exchange token
                if not (stock.get('instrument_token') or stock.get('exchange_token')):
                    logger.warning(f"Missing token for {symbol}")
                    continue

                # Add any additional fields if missing
                validated_stock = {
                    'tradingsymbol': symbol,
                    'name': stock.get('name', symbol),
                    'instrument_token': stock.get('instrument_token', stock.get('exchange_token')),
                    'exchange': stock.get('exchange', 'NSE'),
                    'segment': stock.get('segment', 'NSE'),
                }

                valid_stocks.append(validated_stock)
                logger.debug(f"Validated stock: {symbol}")

            except Exception as e:
                logger.error(f"Error validating stock: {str(e)}")
                continue

        return valid_stocks

    @staticmethod
    def check_data_freshness(df: pd.DataFrame, max_age_days: int = 5) -> bool:
        """Check if the data is fresh enough"""
        if df is None or df.empty:
            return False

        latest_timestamp = df.index.max()
        age = datetime.now(pytz.timezone('Asia/Kolkata')) - latest_timestamp.tz_localize('Asia/Kolkata')
        
        # For daily data, we consider weekdays only
        business_days = np.busday_count(
            latest_timestamp.date(),
            datetime.now(pytz.timezone('Asia/Kolkata')).date()
        )
        
        if business_days > max_age_days:
            logger.warning(f"Data is {business_days} business days old")
            return False
            
        return True 