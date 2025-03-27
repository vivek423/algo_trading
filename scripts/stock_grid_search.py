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
import traceback
import glob

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

def run_stock_grid_search(input_data_path: Optional[str] = None, 
                          stock_symbol: str = None, 
                          output_dir: str = None, 
                          input_dir: Optional[str] = None,
                          max_combinations: int = None, 
                          max_investment: float = 5000, 
                          initial_capital: float = 10000,
                          metric: str = 'sharpe_ratio',
                          trading_config: Optional[str] = None):
    """Run grid search for a specific stock and save its optimal configuration."""
    logging.info(f"Running grid search for {stock_symbol}")
    
    # Create stock-specific output directory
    stock_output_dir = os.path.join(output_dir, stock_symbol)
    os.makedirs(stock_output_dir, exist_ok=True)
    
    # Set up stock-specific logging
    logger = setup_logging(stock_output_dir)
    
    try:
        # Initialize grid search optimizer with stock-specific parameters
        optimizer = GridSearchOptimizer(
            data_path=input_data_path,
            input_dir=input_dir,
            output_dir=stock_output_dir,
            max_investment_per_trade=max_investment,
            initial_capital=initial_capital,
            stocks=[stock_symbol],
            trading_config=trading_config
        )
        
        # Run grid search
        results = optimizer.run_grid_search(max_combinations)
        
        # Check if we got valid results
        if not results:
            logger.warning(f"No valid grid search results for {stock_symbol}")
            
            # Create default parameters for the stock
            default_params = get_default_parameters()
            
            # Save default configuration - fallback to ensure we have a config file
            stock_config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'stock_configs')
            config_path = save_stock_config(stock_symbol, default_params, stock_config_dir)
            
            logger.info(f"Created default configuration for {stock_symbol} at {config_path}")
            
            # Return basic result with default parameters
            return {
                'symbol': stock_symbol,
                'metric': metric,
                'value': 0,
                'params': default_params,
                'num_trades': 0,
                'win_rate': 0,
                'final_capital': initial_capital,
                'realized_pnl': 0,
                'config_path': config_path
            }
        
        # If we have results, log some details about them
        logger.info(f"Grid search complete for {stock_symbol}. {len(results)} valid combinations found.")
        logger.info(f"Top {min(3, len(results))} configurations:")
        
        # Log top configurations
        for i, result in enumerate(results[:3]):
            logger.info(f"Configuration {i+1}:")
            logger.info(f"  Metric ({metric}): {result.get(metric, 0)}")
            
            # Safely access trades count
            if 'num_trades' in result:
                logger.info(f"  Trades: {result['num_trades']}")
            elif 'total_trades' in result:
                logger.info(f"  Trades: {result['total_trades']}")
            else:
                logger.info(f"  Trades: Unknown")
            
            # Use get() with defaults for safe access to dictionary keys
            logger.info(f"  Win Rate: {result.get('win_rate', 0):.2f}%")
            logger.info(f"  Sharpe Ratio: {result.get('sharpe_ratio', 0):.2f}")
            logger.info(f"  CAGR: {result.get('cagr', 0):.2f}%")
            logger.info(f"  Max Drawdown: {result.get('max_drawdown', 0):.2f}%")
            
            # Handle different key names for profit/loss
            if 'realized_pnl' in result:
                logger.info(f"  Profit & Loss: ₹{result['realized_pnl']:.2f}")
            else:
                logger.info(f"  Profit & Loss: ₹{result.get('final_capital', 0) - initial_capital:.2f}")
                
            # Handle different parameter key names
            if 'params' in result:
                logger.info(f"  Parameters: {result['params']}")
            elif 'parameters' in result:
                logger.info(f"  Parameters: {result['parameters']}")
            else:
                logger.info(f"  Parameters: Unknown")
                
            logger.info("-----")
            
        # Save the best configuration
        best_result = results[0]
        logger.info(f"Best configuration for {stock_symbol}:")
        logger.info(f"  Metric: {metric}")
        logger.info(f"  Value: {best_result.get(metric, 0)}")
        
        # Debug the best_result keys
        logger.debug(f"Best result keys: {list(best_result.keys())}")
        
        # Extract parameters from appropriate key
        if 'params' in best_result:
            best_params = best_result['params']
        elif 'parameters' in best_result:
            best_params = best_result['parameters']
        else:
            # Look through all keys for anything that might be parameters
            parameter_keys = [k for k in best_result.keys() if 'param' in k.lower()]
            if parameter_keys:
                best_params = best_result[parameter_keys[0]]
            else:
                logger.warning(f"Unable to find parameters in grid search result. Available keys: {list(best_result.keys())}")
                best_params = get_default_parameters()
        
        # Save the configuration to file
        stock_config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'stock_configs')
        config_path = save_stock_config(stock_symbol, best_params, stock_config_dir)
        
        logger.info(f"Saved configuration to {config_path}")
        
        # Standardize result fields for return
        num_trades = best_result.get('num_trades', best_result.get('total_trades', 0))
        final_capital = best_result.get('final_capital', 0)
        realized_pnl = best_result.get('realized_pnl', final_capital - initial_capital)
        
        return {
            'symbol': stock_symbol,
            'metric': metric,
            'value': best_result.get(metric, 0),
            'params': best_params,
            'num_trades': num_trades,
            'win_rate': best_result.get('win_rate', 0),
            'final_capital': final_capital,
            'realized_pnl': realized_pnl,
            'config_path': config_path
        }
        
    except Exception as e:
        logger.error(f"Error running grid search for {stock_symbol}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Create default parameters for the stock
        default_params = get_default_parameters()
        
        # Save default configuration even if grid search failed
        stock_config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'stock_configs')
        config_path = save_stock_config(stock_symbol, default_params, stock_config_dir)
        
        logger.info(f"Created default configuration for {stock_symbol} due to error: {config_path}")
        
        # Return basic result with default parameters
        return {
            'symbol': stock_symbol,
            'metric': metric,
            'value': 0,
            'params': default_params,
            'num_trades': 0,
            'win_rate': 0,
            'final_capital': initial_capital,
            'realized_pnl': 0,
            'config_path': config_path
        }

def get_default_parameters():
    """Return default technical analysis parameters."""
    return {
        'macd': {
            'fast_period': 12,
            'slow_period': 26,
            'signal_period': 9
        },
        'support_resistance': {
            'support_period': 14,
            'resistance_period': 14
        },
        'atr': {
            'window': 14
        },
        'ema': {
            'period': 20
        },
        'bollinger_bands': {
            'length': 20,
            'std': 2.0
        },
        'rsi': {
            'length': 14,
            'oversold': 30,
            'overbought': 70
        },
        'risk_management': {
            'stop_loss_atr_multiplier': 2.0,
            'take_profit_atr_multiplier': 3.0
        }
    }

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
        
        # Get existing stocks list or initialize it
        if 'stocks' not in trading_config or not trading_config['stocks']:
            trading_config['stocks'] = []
            existing_stocks = set()
        else:
            # Extract existing stock symbols
            existing_stocks = set()
            for stock_entry in trading_config['stocks']:
                if isinstance(stock_entry, dict) and 'symbol' in stock_entry:
                    existing_stocks.add(stock_entry['symbol'])
                elif isinstance(stock_entry, str):
                    existing_stocks.add(stock_entry)
        
        # Update stocks section with new configs
        updated_stocks = []
        for stock_config in stock_configs:
            if not stock_config:  # Skip invalid configs
                continue
                
            symbol = stock_config['symbol']
            
            # Stock has a config path directly in the result
            if 'config_path' in stock_config:
                config_path = stock_config['config_path']
                updated_stocks.append({
                    'symbol': symbol,
                    'config': config_path
                })
                logging.info(f"Added/updated configuration for {symbol}: {config_path}")
            else:
                # Fall back to the standard location
                config_path = f"config/stock_configs/{symbol}.yaml"
                if os.path.exists(config_path):
                    updated_stocks.append({
                        'symbol': symbol,
                        'config': config_path
                    })
                    logging.info(f"Added/updated configuration for {symbol}: {config_path}")
                else:
                    logging.warning(f"Configuration file not found for {symbol}")
        
        # Set the updated stocks list
        trading_config['stocks'] = updated_stocks
        
        # Save the updated config
        with open(trading_config_path, 'w') as f:
            yaml.dump(trading_config, f, default_flow_style=False)
            
        logging.info(f"Updated trading config with {len(updated_stocks)} stock-specific configurations")
        return True
        
    except Exception as e:
        logging.error(f"Error updating trading config: {str(e)}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Main function to run stock-specific grid search"""
    parser = argparse.ArgumentParser(description='Run stock-specific grid search')
    parser.add_argument('--input-dir', type=str, help='Directory containing input CSV files')
    parser.add_argument('--input', type=str, help='Single input CSV file with multiple stocks')
    parser.add_argument('--stocks', type=str, nargs='+', help='Stock symbols to process')
    parser.add_argument('--trading-config', type=str, help='Path to trading configuration file')
    parser.add_argument('--max-combinations', type=int, default=10000, help='Maximum number of combinations to test')
    parser.add_argument('--max-investment', type=float, default=5000, help='Maximum investment per trade')
    parser.add_argument('--initial-capital', type=float, default=10000, help='Initial capital')
    parser.add_argument('--metric', choices=['sharpe_ratio', 'cagr', 'win_rate', 'total_pnl'], 
                       default='sharpe_ratio', help='Performance metric to optimize')
    
    args = parser.parse_args()
    
    # Hardcoded output directory
    output_dir = 'data/outputs/stock_grid_search'
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize list to store stock symbols
    stock_symbols = []
    
    # Determine which stocks to process
    if args.stocks:
        stock_symbols = args.stocks
    elif args.trading_config:
        # Load from trading config
        with open(args.trading_config, 'r') as f:
            trading_config = yaml.safe_load(f)
            
        # Handle different formats of stocks configuration
        if isinstance(trading_config['stocks'], list):
            if trading_config['stocks'] and isinstance(trading_config['stocks'][0], dict):
                # New format: list of dicts with symbol and config
                stock_symbols = [entry['symbol'] for entry in trading_config['stocks']]
            else:
                # Old format: just list of symbols
                stock_symbols = trading_config['stocks']
        else:
            logger.error("Invalid stocks configuration in trading config")
            return
    else:
        logger.error("Either --stocks or --trading-config must be specified")
        return
        
    logger.info(f"Processing {len(stock_symbols)} stocks for optimization")
        
    # For each stock, run grid search
    for symbol in stock_symbols:
        logger.info(f"Starting optimization for {symbol}")
        
        try:
            # Get data for this stock
            if args.input_dir:
                # Try different file patterns
                file_patterns = [
                    f"{symbol}_day.csv",
                    f"{symbol}_1day.csv", 
                    f"{symbol}*.csv"
                ]
                
                stock_file = None
                for pattern in file_patterns:
                    matches = glob.glob(os.path.join(args.input_dir, pattern))
                    if matches:
                        stock_file = matches[0]
                        break
                        
                if not stock_file:
                    logger.error(f"Could not find data file for {symbol} in {args.input_dir}")
                    continue
                    
                # Load the stock data
                df = pd.read_csv(stock_file)
                logger.info(f"Loaded data for {symbol} from {stock_file} with shape {df.shape}")
                
                # Add symbol column if not present
                if 'symbol' not in df.columns:
                    df['symbol'] = symbol
                    
            elif args.input:
                # Load from combined file and filter
                all_data = pd.read_csv(args.input)
                df = all_data[all_data['symbol'] == symbol].copy()
                logger.info(f"Filtered data for {symbol} from {args.input} with shape {df.shape}")
                
                if df.empty:
                    logger.error(f"No data found for {symbol} in {args.input}")
                    continue
            else:
                logger.error("Either --input-dir or --input must be specified")
                continue
                
            # Make sure we have a timestamp column
            if 'timestamp' not in df.columns:
                logger.error(f"Missing 'timestamp' column in data for {symbol}")
                continue
                
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Generate parameter grid
            param_grid, parameter_info = generate_parameter_grid()
            
            # Limit combinations if needed
            if args.max_combinations and len(param_grid) > args.max_combinations:
                logger.info(f"Limiting to {args.max_combinations} combinations (from {len(param_grid)})")
                param_grid = param_grid[:args.max_combinations]
            
            # Run grid search for this stock
            results_df = run_grid_search(df, param_grid, args.initial_capital, args.max_investment)
            
            # Calculate metrics
            results_df = calculate_metrics(results_df, args.metric)
            
            # Sort by selected metric in descending order
            results_df = results_df.sort_values(by=args.metric, ascending=False)
            
            # Create stock-specific output directory
            stock_output_dir = os.path.join(output_dir, symbol)
            os.makedirs(stock_output_dir, exist_ok=True)
            
            # Save results for this stock
            results_file = os.path.join(stock_output_dir, 'grid_search_results.csv')
            results_df.to_csv(results_file, index=False)
            
            # Save top configurations
            top_configs = format_configurations(results_df.head(10), parameter_info)
            
            # Save top configs to YAML file
            top_configs_file = os.path.join(stock_output_dir, 'top_configurations.yaml')
            with open(top_configs_file, 'w') as f:
                yaml.dump(top_configs, f, default_flow_style=False)
                
            # Save best config as a separate file for easy access
            best_config_file = os.path.join(stock_output_dir, 'best_config.yaml')
            with open(best_config_file, 'w') as f:
                yaml.dump(top_configs[0], f, default_flow_style=False)
                
            # Also save to the conventional location for the update_config.py script
            stock_config_dir = os.path.join('config', 'stock_configs')
            os.makedirs(stock_config_dir, exist_ok=True)
            stock_config_file = os.path.join(stock_config_dir, f"{symbol}.yaml")
            with open(stock_config_file, 'w') as f:
                yaml.dump(top_configs[0], f, default_flow_style=False)
                
            logger.info(f"Optimization complete for {symbol}")
            logger.info(f"Best {args.metric}: {results_df.iloc[0][args.metric]:.4f}")
            logger.info(f"Results saved to {stock_output_dir}")
            
        except Exception as e:
            logger.error(f"Error processing {symbol}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            continue
            
    logger.info(f"Stock grid search completed for {len(stock_symbols)} stocks")
    print(f"\nStock grid search complete")
    print(f"Results saved to {output_dir}")
    print("Stock-specific configurations saved to config/stock_configs/")
    print("These configs will be automatically used by the technical_analysis.py script with --all option")

if __name__ == "__main__":
    main() 