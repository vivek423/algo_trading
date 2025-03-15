#!/usr/bin/env python3
import os
import yaml
import argparse
import logging
import sys
import pandas as pd
from typing import List, Dict, Optional
import tempfile
import shutil

# Import the grid search optimizer
from grid_search import GridSearchOptimizer, setup_logging
from update_config import update_config

def load_trading_config(config_path: str) -> Dict:
    """Load the trading configuration file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def save_stock_config(stock_symbol: str, params: Dict, config_dir: str):
    """Save stock-specific configuration."""
    os.makedirs(config_dir, exist_ok=True)
    
    # Prepare the config with stock parameters
    config_path = os.path.join(config_dir, f"{stock_symbol}.yaml")
    
    # Add columns section if not exists
    if 'columns' not in params:
        params['columns'] = {
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'timestamp': 'timestamp'
        }
    
    # Create a formatted config with comments
    formatted_config = """# Technical Analysis Parameters - Optimized via Grid Search for {stock}

# MACD Parameters
macd:
  fast_period: {macd_fast}
  slow_period: {macd_slow}
  signal_period: {macd_signal}

# Support and Resistance Parameters
support_resistance:
  support_period: {support_period}
  resistance_period: {resistance_period}

# ATR Parameters
atr:
  window: {atr_window}

# EMA Parameters
ema:
  period: {ema_period}

# Bollinger Bands Parameters
bollinger_bands:
  length: {bb_length}
  std: {bb_std}

# RSI Parameters
rsi:
  length: {rsi_length}
  oversold: {rsi_oversold}
  overbought: {rsi_overbought}

# Risk Management Parameters
risk_management:
  stop_loss_atr_multiplier: {sl_multiplier}
  take_profit_atr_multiplier: {tp_multiplier}

# Default column names
columns:
  open: 'open'
  high: 'high'
  low: 'low'
  close: 'close'
  volume: 'volume'
  timestamp: 'timestamp'
""".format(
        stock=stock_symbol,
        macd_fast=params['macd']['fast_period'],
        macd_slow=params['macd']['slow_period'],
        macd_signal=params['macd']['signal_period'],
        support_period=params['support_resistance']['support_period'],
        resistance_period=params['support_resistance']['resistance_period'],
        atr_window=params['atr']['window'],
        ema_period=params['ema']['period'],
        bb_length=params['bollinger_bands']['length'],
        bb_std=params['bollinger_bands']['std'],
        rsi_length=params['rsi']['length'],
        rsi_oversold=params['rsi']['oversold'],
        rsi_overbought=params['rsi']['overbought'],
        sl_multiplier=params['risk_management']['stop_loss_atr_multiplier'],
        tp_multiplier=params['risk_management']['take_profit_atr_multiplier']
    )
    
    # Write the stock-specific config
    with open(config_path, 'w') as f:
        f.write(formatted_config)
    
    logging.info(f"Saved stock-specific configuration for {stock_symbol} to {config_path}")
    return config_path

def run_stock_grid_search(input_data_path: str, stock_symbol: str, output_dir: str, max_combinations: int = None, 
                          max_investment: float = 5000, initial_capital: float = 10000,
                          metric: str = 'sharpe_ratio'):
    """Run grid search for a specific stock and save its optimal configuration."""
    logging.info(f"Running grid search for {stock_symbol}")
    
    # Create stock-specific output directory
    stock_output_dir = os.path.join(output_dir, stock_symbol)
    os.makedirs(stock_output_dir, exist_ok=True)
    
    # Set up stock-specific logging
    logger = setup_logging(stock_output_dir)
    
    try:
        # Load the data
        df = pd.read_csv(input_data_path)
        
        # Filter data for this stock only
        stock_data = df[df['symbol'] == stock_symbol].copy()
        
        if len(stock_data) < 10:
            logger.warning(f"Not enough data for {stock_symbol} (only {len(stock_data)} rows). Skipping.")
            return None
            
        # Create a temporary file with just this stock's data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            stock_data_path = temp_file.name
            stock_data.to_csv(temp_file, index=False)
        
        try:
            # Initialize grid search optimizer
            optimizer = GridSearchOptimizer(
                stock_data_path, 
                stock_output_dir,
                max_investment_per_trade=max_investment,
                initial_capital=initial_capital
            )
            
            # Run grid search
            results = optimizer.run_grid_search(max_combinations)
            
            if not results:
                logger.warning(f"No valid results for {stock_symbol}")
                return None
                
            # Sort results by the specified metric
            if metric == 'sharpe_ratio':
                results.sort(key=lambda x: x['sharpe_ratio'], reverse=True)
            elif metric == 'cagr':
                results.sort(key=lambda x: x['cagr'], reverse=True)
            elif metric == 'win_rate':
                results.sort(key=lambda x: x['win_rate'], reverse=True)
                
            # Get the best parameters
            best_params = results[0]['parameters']
            
            # Save stock-specific configuration
            config_dir = os.path.join('config', 'stock_configs')
            config_path = save_stock_config(stock_symbol, best_params, config_dir)
            
            # Print summary
            logger.info(f"Stock {stock_symbol} - Best {metric}: {results[0][metric]:.4f}")
            logger.info(f"Stock {stock_symbol} - CAGR: {results[0]['cagr']:.2f}%")
            logger.info(f"Stock {stock_symbol} - Win Rate: {results[0]['win_rate']:.2f}%")
            logger.info(f"Stock {stock_symbol} - Configuration saved to {config_path}")
            
            return {
                'symbol': stock_symbol,
                'metric_value': results[0][metric],
                'cagr': results[0]['cagr'],
                'win_rate': results[0]['win_rate'],
                'config_path': config_path
            }
        finally:
            # Clean up the temporary file
            if os.path.exists(stock_data_path):
                os.remove(stock_data_path)
    
    except Exception as e:
        logger.error(f"Error running grid search for {stock_symbol}: {str(e)}")
        return None

def update_trading_config(trading_config_path: str, stock_configs: List[Dict]):
    """Update the trading configuration file with stock-specific configs."""
    try:
        # Load current trading config
        with open(trading_config_path, 'r') as f:
            trading_config = yaml.safe_load(f)
        
        # Create backup of the original config
        backup_path = f"{trading_config_path}.bak"
        shutil.copy2(trading_config_path, backup_path)
        logging.info(f"Created backup of trading config: {backup_path}")
        
        # Update stocks section with configs
        stocks = []
        for stock_config in stock_configs:
            if stock_config:  # Only include stocks with valid results
                stocks.append({
                    'symbol': stock_config['symbol'],
                    'config': stock_config['config_path']
                })
        
        # Update the trading config
        trading_config['stocks'] = stocks
        
        # Save the updated config
        with open(trading_config_path, 'w') as f:
            yaml.dump(trading_config, f, default_flow_style=False)
            
        logging.info(f"Updated trading config with {len(stocks)} stock-specific configurations")
        
    except Exception as e:
        logging.error(f"Error updating trading config: {str(e)}")

def main():
    """Main function to run grid search on individual stocks."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    parser = argparse.ArgumentParser(description='Run grid search for individual stocks')
    parser.add_argument('--input', required=True, help='Path to input CSV file with combined OHLC data for all stocks')
    parser.add_argument('--output', required=True, help='Directory to save results')
    parser.add_argument('--trading-config', default='config/trading_config.yaml', help='Path to trading configuration file')
    parser.add_argument('--max-combinations', type=int, default=100, help='Maximum number of combinations to test per stock')
    parser.add_argument('--max-investment', type=float, default=5000, help='Maximum investment per trade')
    parser.add_argument('--initial-capital', type=float, default=10000, help='Initial capital for portfolio')
    parser.add_argument('--metric', choices=['sharpe_ratio', 'cagr', 'win_rate'], default='sharpe_ratio',
                        help='Metric to optimize for')
    parser.add_argument('--stocks', nargs='+', help='Specific stocks to process (if not specified, uses trading config)')
    
    args = parser.parse_args()
    
    try:
        # Create output directory
        os.makedirs(args.output, exist_ok=True)
        
        # Determine which stocks to process
        if args.stocks:
            stock_symbols = args.stocks
            logging.info(f"Processing specified stocks: {', '.join(stock_symbols)}")
        else:
            # Load from trading config
            trading_config = load_trading_config(args.trading_config)
            
            # Check if trading config has the new format
            if trading_config['stocks'] and isinstance(trading_config['stocks'][0], dict):
                stock_symbols = [stock['symbol'] for stock in trading_config['stocks']]
            else:
                # Old format - just a list of symbols
                stock_symbols = trading_config['stocks']
                
            logging.info(f"Processing stocks from trading config: {', '.join(stock_symbols)}")
        
        # Run grid search for each stock
        stock_configs = []
        for symbol in stock_symbols:
            result = run_stock_grid_search(
                args.input, symbol, args.output, 
                args.max_combinations, args.max_investment, 
                args.initial_capital, args.metric
            )
            if result:
                stock_configs.append(result)
        
        # Update trading config with stock-specific configs
        update_trading_config(args.trading_config, stock_configs)
        
        # Print summary
        print("\nGrid Search Summary:")
        print(f"Total stocks processed: {len(stock_symbols)}")
        print(f"Stocks with valid results: {len(stock_configs)}")
        
        if stock_configs:
            # Sort by the specified metric
            if args.metric == 'sharpe_ratio':
                stock_configs.sort(key=lambda x: x['metric_value'], reverse=True)
            elif args.metric == 'cagr':
                stock_configs.sort(key=lambda x: x['cagr'], reverse=True)
            elif args.metric == 'win_rate':
                stock_configs.sort(key=lambda x: x['win_rate'], reverse=True)
                
            # Print top stocks
            print("\nTop performing stocks:")
            for i, config in enumerate(stock_configs[:5], 1):
                print(f"{i}. {config['symbol']} - {args.metric}: {config['metric_value']:.4f}, "
                      f"CAGR: {config['cagr']:.2f}%, Win Rate: {config['win_rate']:.2f}%")
        
        logging.info("Stock-specific grid search completed successfully")
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 