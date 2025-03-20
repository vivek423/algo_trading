#!/usr/bin/env python3
import pandas as pd
import numpy as np
import os
import sys
import logging
import yaml
import glob
from datetime import datetime, timedelta
import pytz
from technical_analysis import TechnicalAnalysis
import argparse
from typing import Dict, List, Optional, Set

# Import WhatsApp notifier
try:
    from whatsapp_notifier import WhatsAppNotifier
    WHATSAPP_AVAILABLE = True
except ImportError:
    WHATSAPP_AVAILABLE = False

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'recommendations.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger(__name__)

class RecommendationGenerator:
    def __init__(self, config_path: str, max_investment: float = 50000.0, enable_notifications: bool = True):
        """
        Initialize Recommendation Generator.
        
        Args:
            config_path: Path to trading configuration file
            max_investment: Maximum investment per stock (Rs)
            enable_notifications: Whether to send WhatsApp notifications
        """
        self.config_path = config_path
        self.max_investment = max_investment
        self.enable_notifications = enable_notifications
        
        # Setup directories
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.stock_dir = os.path.join(self.data_dir, 'inputs')
        self.recommendations_dir = os.path.join(self.data_dir, 'recommendations')
        
        # Create recommendations directory if it doesn't exist
        os.makedirs(self.recommendations_dir, exist_ok=True)
        
        # Initialize WhatsApp notifier if enabled and available
        self.notifier = None
        if self.enable_notifications and WHATSAPP_AVAILABLE:
            try:
                self.notifier = WhatsAppNotifier()
                logger.info("WhatsApp notifier initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize WhatsApp notifier: {str(e)}")
                self.notifier = None
        
        # Load trading configuration
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Loaded trading configuration from {config_path}")
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            self.config = {}
        
        # Track stocks that have already been recommended today
        self.ist_timezone = pytz.timezone('Asia/Kolkata')
        self.today = datetime.now(self.ist_timezone).strftime('%Y-%m-%d')
        self.recommended_stocks: Set[str] = set()
        
        # Format date for filename (YYYYMMDD)
        date_for_file = self.today.replace('-', '')
        
        # Load previously recommended stocks if file exists
        self.today_file = os.path.join(self.recommendations_dir, f"stock_recommendations_{date_for_file}.csv")
        
        # Also save to a fixed "latest" file for convenience
        self.latest_file = os.path.join(self.recommendations_dir, "latest_recommendations.csv")
        
        if os.path.exists(self.today_file):
            try:
                df = pd.read_csv(self.today_file)
                self.recommended_stocks = set(df['symbol'].unique())
                logger.info(f"Loaded {len(self.recommended_stocks)} previously recommended stocks for today")
            except Exception as e:
                logger.error(f"Error loading previous recommendations: {str(e)}")
    
    def get_stock_configs(self) -> Dict[str, str]:
        """Get stock-specific configuration paths."""
        stock_configs = {}
        
        if not self.config['stocks']:
            logger.warning("No stocks found in configuration")
            return stock_configs
        
        # Check if stocks are in the new format (list of dicts)
        if isinstance(self.config['stocks'][0], dict):
            for stock_entry in self.config['stocks']:
                if 'symbol' in stock_entry and 'config' in stock_entry:
                    stock_configs[stock_entry['symbol']] = stock_entry['config']
        # Old format (list of strings)
        else:
            stocks_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'stock_configs')
            for symbol in self.config['stocks']:
                config_path = os.path.join(stocks_dir, f"{symbol}.yaml")
                if os.path.exists(config_path):
                    stock_configs[symbol] = config_path
        
        return stock_configs
    
    def calculate_quantity(self, price: float) -> int:
        """
        Calculate quantity of shares to buy based on price and max investment.
        
        Args:
            price: Current price of the stock
            
        Returns:
            int: Quantity to buy (0 if price is too high)
        """
        if price <= 0:
            return 0
        
        if price > self.max_investment:
            return 0
        
        return int(self.max_investment / price)
    
    def analyze_stock(self, symbol: str, config_path: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Analyze a stock and check for buy signals.
        
        Args:
            symbol: Stock symbol
            config_path: Path to stock-specific configuration (optional)
            
        Returns:
            DataFrame with buy signals or None if no signals
        """
        try:
            # Skip if stock already recommended today
            if symbol in self.recommended_stocks:
                logger.debug(f"Skipping {symbol} - already recommended today")
                return None
                
            # Get input file path
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'inputs')
            input_file = os.path.join(data_dir, f"{symbol}_day.csv")
            
            if not os.path.exists(input_file):
                logger.warning(f"Input file not found for {symbol}: {input_file}")
                return None
            
            # Initialize technical analysis with stock-specific config if available
            ta = TechnicalAnalysis(config_path=config_path)
            
            # Load data
            df = ta.load_data(input_file)
            
            # Calculate indicators
            df = ta.calculate_all_indicators(df)
            
            # Check for buy signals in the most recent data point
            latest_data = df.iloc[-1:].copy()
            
            if latest_data.empty:
                logger.warning(f"No data found for {symbol}")
                return None
                
            # Check if the latest data point has a buy signal (1)
            if latest_data['signal_combined'].iloc[0] == 1:
                # Add symbol and timestamp
                latest_data['symbol'] = symbol
                latest_data['recommendation_time'] = datetime.now(self.ist_timezone).strftime('%Y-%m-%d %H:%M:%S')
                
                # Calculate quantity to buy
                latest_data['quantity'] = self.calculate_quantity(latest_data['close'].iloc[0])
                
                # Reset index to make timestamp a column
                latest_data = latest_data.reset_index()
                
                logger.info(f"Found buy signal for {symbol} at price {latest_data['close'].iloc[0]:.2f}")
                return latest_data
                
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {str(e)}")
            return None
    
    def generate_recommendations(self) -> pd.DataFrame:
        """
        Generate stock recommendations for all configured stocks.
        
        Returns:
            DataFrame with recommendations
        """
        # Get stock-specific configurations
        stock_configs = self.get_stock_configs()
        logger.info(f"Processing {len(stock_configs)} stocks")
        
        recommendations = []
        
        # Process each stock
        for symbol, config_path in stock_configs.items():
            recommendation = self.analyze_stock(symbol, config_path)
            if recommendation is not None and not recommendation.empty:
                recommendations.append(recommendation)
                self.recommended_stocks.add(symbol)
        
        # Combine all recommendations
        if recommendations:
            combined_df = pd.concat(recommendations, ignore_index=True)
            
            # Select relevant columns for the output
            columns = [
                'symbol', 'timestamp', 'recommendation_time', 'open', 'high', 'low', 'close', 
                'quantity', 'stop_loss', 'take_profit', 'macd_line', 'macd_signal', 'macd_hist',
                'rsi', 'atr', 'signal_combined'
            ]
            
            # Filter columns that exist
            available_columns = [col for col in columns if col in combined_df.columns]
            result_df = combined_df[available_columns]
            
            # Save to CSV
            self._save_recommendations(result_df)
            
            # Send WhatsApp notification if enabled
            if self.enable_notifications:
                self._send_notification(result_df)
            
            logger.info(f"Generated {len(result_df)} stock recommendations")
            return result_df
        else:
            logger.info("No buy signals found for any stocks")
            return pd.DataFrame()
    
    def _save_recommendations(self, df: pd.DataFrame) -> None:
        """Save recommendations to CSV file."""
        if df.empty:
            return
            
        # Check if file exists and append if it does
        if os.path.exists(self.today_file):
            # Read existing recommendations
            existing_df = pd.read_csv(self.today_file)
            
            # Append new recommendations
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            
            # Remove duplicates based on symbol
            combined_df = combined_df.drop_duplicates(subset=['symbol'], keep='first')
            
            # Save combined recommendations
            combined_df.to_csv(self.today_file, index=False)
            # Also save to latest file
            combined_df.to_csv(self.latest_file, index=False)
            logger.info(f"Updated recommendations saved to {self.today_file}")
        else:
            # Save new recommendations
            df.to_csv(self.today_file, index=False)
            # Also save to latest file
            df.to_csv(self.latest_file, index=False)
            logger.info(f"New recommendations saved to {self.today_file}")
    
    def _send_notification(self, df: pd.DataFrame) -> None:
        """
        Send WhatsApp notification with recommendations.
        
        Args:
            df: DataFrame containing recommendations
        """
        if not self.enable_notifications or self.notifier is None or df.empty:
            return
        
        try:
            # Get buy recommendations only
            buy_recommendations = df[df['recommendation'] == 'BUY']
            
            if buy_recommendations.empty:
                logger.info("No buy recommendations to send notification for")
                return
            
            # Format data for notification
            recommendations = []
            for _, row in buy_recommendations.iterrows():
                recommendations.append({
                    'symbol': row['symbol'],
                    'close': row['close_price'],
                    'quantity': row['max_quantity'],
                    'stop_loss': row['stop_loss'] if 'stop_loss' in row and pd.notna(row['stop_loss']) else 0.0,
                    'take_profit': row['take_profit'] if 'take_profit' in row and pd.notna(row['take_profit']) else 0.0
                })
            
            # Send notification
            if self.notifier.send_recommendation_alert(recommendations):
                logger.info(f"WhatsApp notification sent for {len(recommendations)} stock recommendations")
            else:
                logger.warning("Failed to send WhatsApp notification")
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp notification: {str(e)}")
    
    def send_eod_summary(self, date: Optional[str] = None) -> None:
        """
        Send end-of-day trading summary via WhatsApp.
        
        Args:
            date: Optional date string in YYYY-MM-DD format. If None, uses today's date.
        """
        if not self.enable_notifications or self.notifier is None:
            logger.warning("Notifications not enabled or WhatsApp notifier not available")
            return
            
        try:
            # Send EOD summary
            if self.notifier.send_trading_summary(date):
                logger.info("End-of-day trading summary sent successfully")
            else:
                logger.warning("Failed to send end-of-day trading summary")
                
        except Exception as e:
            logger.error(f"Error sending end-of-day summary: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Generate stock recommendations')
    parser.add_argument('--config', '-c', default='config/trading_config.yaml', 
                        help='Path to trading configuration file')
    parser.add_argument('--max-investment', '-m', type=float, default=50000.0,
                        help='Maximum investment per stock (Rs)')
    parser.add_argument('--notifications', '-n', action='store_true',
                        help='Enable WhatsApp notifications')
    parser.add_argument('--eod-summary', '-e', action='store_true',
                        help='Send end-of-day summary (without generating new recommendations)')
    parser.add_argument('--date', '-d', type=str,
                        help='Date for EOD summary in YYYY-MM-DD format (defaults to today)')
    
    args = parser.parse_args()
    
    # Create recommendation generator
    generator = RecommendationGenerator(
        config_path=args.config,
        max_investment=args.max_investment,
        enable_notifications=args.notifications
    )
    
    # Handle EOD summary mode
    if args.eod_summary:
        logger.info("Sending end-of-day summary")
        generator.send_eod_summary(args.date)
        return
    
    # Generate recommendations
    recommendations = generator.generate_recommendations()
    
    # Print summary
    if not recommendations.empty:
        print("\nStock Recommendations Summary:")
        print("=" * 80)
        for _, row in recommendations.iterrows():
            print(f"{row['symbol']}: ₹{row['close_price']:.2f} | Quantity: {row['max_quantity']} | "
                  f"Stop Loss: ₹{row['stop_loss']:.2f} | Take Profit: ₹{row['take_profit']:.2f}")
        print("=" * 80)
        print(f"Total recommendations: {len(recommendations)}")
        
        if args.notifications:
            print("WhatsApp notification has been sent!")
    else:
        print("\nNo buy signals detected for any stocks at this time.")
    
    # Send EOD summary if it's end of day (after 4:00 PM IST)
    ist_now = datetime.now(pytz.timezone('Asia/Kolkata'))
    if ist_now.hour >= 16 and args.notifications:
        logger.info("Sending end-of-day summary after recommendation generation")
        generator.send_eod_summary()

if __name__ == "__main__":
    main() 