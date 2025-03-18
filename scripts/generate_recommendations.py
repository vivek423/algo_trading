#!/usr/bin/env python3
"""
Generate daily stock recommendations based on technical analysis.
Creates a CSV file with clear buy/sell/hold recommendations for all stocks.
"""

import os
import sys
import pandas as pd
import numpy as np
import logging
import yaml
from datetime import datetime
import argparse
from pathlib import Path

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from scripts.technical_analysis import TechnicalAnalysis
from scripts.performance_analyzer import PerformanceAnalyzer
from scripts.session_manager import SessionManager

# Configure logging
log_dir = os.path.join(project_root, 'logs')
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

def load_trading_config(config_path):
    """Load trading configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading trading config: {str(e)}")
        sys.exit(1)

def load_stock_configs(trading_config_path):
    """Load stock-specific configuration paths"""
    try:
        with open(trading_config_path, 'r') as f:
            trading_config = yaml.safe_load(f)
            
        # Check if trading config has the structured format
        stock_configs = {}
        if isinstance(trading_config['stocks'], list) and isinstance(trading_config['stocks'][0], dict):
            for stock_entry in trading_config['stocks']:
                if 'symbol' in stock_entry and 'config' in stock_entry:
                    stock_configs[stock_entry['symbol']] = stock_entry['config']
        
        logger.info(f"Loaded {len(stock_configs)} stock-specific configurations")
        return stock_configs
        
    except Exception as e:
        logger.error(f"Error loading stock configurations: {str(e)}")
        return {}

def get_latest_data_files(input_dir):
    """Get the latest data file for each stock"""
    latest_files = {}
    
    try:
        for file in os.listdir(input_dir):
            if file.endswith('.csv'):
                # Extract symbol from filename (assuming format like SYMBOL_day.csv)
                parts = file.split('_')
                if len(parts) >= 2:
                    symbol = parts[0]
                    file_path = os.path.join(input_dir, file)
                    
                    # Check if this is newer than any previously found file for this symbol
                    if symbol not in latest_files or os.path.getmtime(file_path) > os.path.getmtime(latest_files[symbol]):
                        latest_files[symbol] = file_path
    except Exception as e:
        logger.error(f"Error finding latest data files: {str(e)}")
    
    return latest_files

def analyze_stock(symbol, data_file, config_path=None):
    """Run technical analysis on a stock and return recent indicators"""
    try:
        # Initialize technical analysis with stock config if available
        ta = TechnicalAnalysis(config_path=config_path)
        
        # Load stock data
        df = pd.read_csv(data_file)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
        
        # Calculate indicators
        df_with_indicators = ta.calculate_all_indicators(df)
        
        # Add symbol column if not present
        if 'symbol' not in df_with_indicators.columns:
            df_with_indicators['symbol'] = symbol
            
        return df_with_indicators.tail(5)  # Return the most recent 5 days
    
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {str(e)}")
        return None

def generate_recommendation(df):
    """Generate buy/sell/hold recommendation based on recent indicators"""
    try:
        if df is None or len(df) == 0:
            return None
        
        # Get the most recent row
        latest = df.iloc[-1]
        
        # Check if we have the necessary columns
        if 'signal_combined' not in latest:
            return {
                'symbol': latest.get('symbol', 'UNKNOWN'),
                'date': latest.name if isinstance(latest.name, pd.Timestamp) else pd.Timestamp.now(),
                'close_price': latest.get('close', 0),
                'recommendation': 'HOLD',
                'stop_loss': 0,
                'take_profit': 0,
                'reason': 'Missing technical indicators'
            }
        
        # Get the recommendation based on the signal_combined value
        # signal_combined is a discrete value: -1 (Sell), 0 (Hold), or 1 (Buy)
        signal = int(latest['signal_combined'])  # Ensure integer value
        
        # Interpret the discrete signal
        if signal == 1:
            recommendation = 'BUY'
            reason = 'Buy signal'
        elif signal == -1:
            recommendation = 'SELL'
            reason = 'Sell signal'
        else:  # signal == 0
            recommendation = 'HOLD'
            reason = 'No clear signal'
        
        # Calculate maximum quantity based on max investment
        max_investment = 50000  # ₹50,000
        price = latest.get('close', 0)
        max_quantity = int(max_investment / price) if price > 0 else 0
        
        # Get stop loss and take profit if available
        stop_loss = latest.get('stop_loss', 0)
        take_profit = latest.get('take_profit', 0)
        
        return {
            'symbol': latest.get('symbol', 'UNKNOWN'),
            'date': latest.name if isinstance(latest.name, pd.Timestamp) else pd.Timestamp.now(),
            'close_price': price,
            'recommendation': recommendation,
            'max_quantity': max_quantity,
            'investment_amount': min(max_quantity * price, max_investment),
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'reason': reason
        }
    
    except Exception as e:
        logger.error(f"Error generating recommendation: {str(e)}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Generate daily stock recommendations')
    parser.add_argument('--input-dir', '-i', default='data/inputs', help='Directory containing input CSV files')
    parser.add_argument('--output-dir', '-o', default='data/recommendations', help='Directory for output recommendations')
    parser.add_argument('--trading-config', '-t', default='config/trading_config.yaml', help='Path to trading configuration')
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load configurations
    trading_config = load_trading_config(args.trading_config)
    stock_configs = load_stock_configs(args.trading_config)
    
    # Get the list of stocks to analyze
    stocks = []
    if isinstance(trading_config['stocks'], list):
        if isinstance(trading_config['stocks'][0], dict):
            stocks = [stock['symbol'] for stock in trading_config['stocks']]
        else:
            stocks = trading_config['stocks']
    
    # Get latest data files
    latest_files = get_latest_data_files(args.input_dir)
    
    # Analyze each stock and generate recommendations
    recommendations = []
    for symbol in stocks:
        logger.info(f"Analyzing {symbol}...")
        
        if symbol not in latest_files:
            logger.warning(f"No data file found for {symbol}")
            continue
        
        # Get the stock-specific config path if available
        config_path = stock_configs.get(symbol)
        
        # Run technical analysis
        result = analyze_stock(symbol, latest_files[symbol], config_path)
        
        # Generate recommendation
        recommendation = generate_recommendation(result)
        if recommendation:
            recommendations.append(recommendation)
    
    # Convert to DataFrame
    if recommendations:
        recommendations_df = pd.DataFrame(recommendations)
        
        # Sort by recommendation type (BUY first, then SELL, then HOLD)
        recommendations_df = recommendations_df.sort_values(by=['recommendation'], 
                                                        ascending=[False])
        
        # Generate timestamp for filename
        timestamp = datetime.now().strftime('%Y%m%d')
        output_file = os.path.join(args.output_dir, f'stock_recommendations_{timestamp}.csv')
        
        # Save to CSV
        recommendations_df.to_csv(output_file, index=False)
        logger.info(f"Recommendations saved to {output_file}")
        
        # Also save a copy with a fixed filename for easy reference
        latest_file = os.path.join(args.output_dir, 'latest_recommendations.csv')
        recommendations_df.to_csv(latest_file, index=False)
        logger.info(f"Latest recommendations saved to {latest_file}")
        
        # Print a summary
        buy_count = len(recommendations_df[recommendations_df['recommendation'] == 'BUY'])
        sell_count = len(recommendations_df[recommendations_df['recommendation'] == 'SELL'])
        hold_count = len(recommendations_df[recommendations_df['recommendation'] == 'HOLD'])
        
        logger.info(f"Generated {len(recommendations_df)} recommendations: {buy_count} BUY, {sell_count} SELL, {hold_count} HOLD")
    else:
        logger.warning("No recommendations generated")

if __name__ == "__main__":
    main() 