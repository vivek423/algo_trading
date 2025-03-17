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
        # Initialize grid search optimizer directly with individual files option
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
        else:
            results.sort(key=lambda x: x['total_profit'], reverse=True)
        
        # Log top 5 results
        logger.info(f"Top results for {stock_symbol}:")
        for i, result in enumerate(results[:5]):
            logger.info(f"Rank {i+1}:")
            if 'num_trades' in result:
                logger.info(f"  Trades: {result['num_trades']}")
            elif 'total_trades' in result:
                logger.info(f"  Trades: {result['total_trades']}")
            else:
                # Log the available keys for debugging
                logger.info(f"  Available keys: {list(result.keys())}")
                logger.info(f"  Trades: Unknown")
                
            logger.info(f"  Win Rate: {result['win_rate']:.2f}%")
            logger.info(f"  Sharpe Ratio: {result['sharpe_ratio']:.2f}")
            logger.info(f"  CAGR: {result['cagr']:.2f}%")
            logger.info(f"  Max Drawdown: {result['max_drawdown']:.2f}%")
            
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
                raise ValueError(f"Unable to find parameters in grid search result. Available keys: {list(best_result.keys())}")
        
        # Save the configuration to file
        stock_config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'stock_configs')
        save_stock_config(stock_symbol, best_params, stock_config_dir)
        
        logger.info(f"Saved configuration to {stock_config_dir}/{stock_symbol}.yaml")
        
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
            'win_rate': best_result['win_rate'],
            'final_capital': final_capital,
            'realized_pnl': realized_pnl
        }
        
    except Exception as e:
        logger.error(f"Error running grid search for {stock_symbol}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
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
    parser = argparse.ArgumentParser(description='Run grid search optimization for specific stocks')
    parser.add_argument('--input', help='Path to input CSV file with combined OHLC data for all stocks')
    parser.add_argument('--input-dir', help='Directory containing individual stock OHLC data files')
    parser.add_argument('--output', required=True, help='Directory to save results')
    parser.add_argument('--trading-config', default='config/trading_config.yaml', 
                       help='Path to trading configuration file')
    parser.add_argument('--stocks', nargs='+', help='Stock symbols to optimize (if omitted, uses all stocks from trading config)')
    parser.add_argument('--max-combinations', type=int, default=1000, help='Maximum number of combinations to test')
    parser.add_argument('--max-investment', type=float, default=5000, help='Maximum investment per trade')
    parser.add_argument('--initial-capital', type=float, default=10000, help='Initial capital for portfolio')
    parser.add_argument('--metric', choices=['sharpe_ratio', 'cagr', 'win_rate'], default='sharpe_ratio',
                      help='Metric to optimize')
    
    args = parser.parse_args()
    
    if not args.input and not args.input_dir:
        print("Error: Either --input or --input-dir must be specified")
        sys.exit(1)
    
    # Load trading config to get stocks if not specified
    if not args.stocks:
        try:
            config = load_trading_config(args.trading_config)
            
            # Handle both formats (list of dicts or list of strings)
            stocks = []
            if isinstance(config.get('stocks'), list):
                for stock in config['stocks']:
                    if isinstance(stock, dict):
                        if 'symbol' in stock:
                            stocks.append(stock['symbol'])
                    else:
                        stocks.append(stock)
            
            if not stocks:
                print("No stocks found in trading config")
                sys.exit(1)
                
            print(f"Loaded {len(stocks)} stocks from trading config")
            
        except Exception as e:
            print(f"Error loading trading config: {str(e)}")
            sys.exit(1)
    else:
        stocks = args.stocks
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Create main log file for summary
    main_logger = setup_logging(args.output)
    main_logger.info(f"Starting grid search for {len(stocks)} stocks")
    main_logger.info(f"Optimizing for {args.metric}")
    
    # Perform grid search for each stock
    stock_results = []
    
    for i, stock in enumerate(stocks):
        main_logger.info(f"Processing stock {i+1}/{len(stocks)}: {stock}")
        
        try:
            result = run_stock_grid_search(
                input_data_path=args.input,
                input_dir=args.input_dir,
                stock_symbol=stock,
                output_dir=args.output,
                max_combinations=args.max_combinations,
                max_investment=args.max_investment,
                initial_capital=args.initial_capital,
                metric=args.metric,
                trading_config=args.trading_config
            )
            
            if result:
                stock_results.append(result)
                main_logger.info(f"Completed grid search for {stock} successfully")
            else:
                main_logger.warning(f"No valid results for {stock}")
                
        except Exception as e:
            main_logger.error(f"Failed to process {stock}: {str(e)}")
    
    # Update trading configuration with stock-specific configs
    updated = update_trading_config(args.trading_config, stock_results)
    
    if updated:
        main_logger.info(f"Updated trading config with {len(stock_results)} stock-specific configurations")
    else:
        main_logger.warning("Failed to update trading config")
    
    # Generate summary
    main_logger.info("\nGrid Search Summary:")
    main_logger.info(f"Total stocks processed: {len(stocks)}")
    main_logger.info(f"Successful optimizations: {len(stock_results)}")
    
    if stock_results:
        # Sort by metric value
        stock_results.sort(key=lambda x: x['value'], reverse=True)
        
        main_logger.info("\nTop 10 Stock Performances:")
        for i, result in enumerate(stock_results[:10]):
            main_logger.info(f"{i+1}. {result['symbol']}: {args.metric}={result['value']:.2f}, " +
                          f"Win Rate={result['win_rate']:.2f}%, Trades={result['num_trades']}, " +
                          f"P&L=₹{result['realized_pnl']:.2f}")
    
    main_logger.info("\nGrid search completed")

if __name__ == "__main__":
    main() 