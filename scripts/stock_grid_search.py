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
from datetime import datetime
from itertools import product
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import the grid search optimizer
from grid_search import GridSearchOptimizer, setup_logging
from update_config import update_config
from technical_analysis import TechnicalAnalysis
from performance_analyzer import PerformanceAnalyzer

def load_trading_config(config_path: str) -> Dict:
    """Load the trading configuration file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def save_stock_config(symbol, best_params, output_dir, start_date=None, end_date=None):
    """
    Save the best parameters for a stock as a YAML configuration file.
    
    Args:
        symbol: Stock symbol
        best_params: Dictionary of best parameters
        output_dir: Directory to save configuration files
        start_date: Start date of the training period (str or datetime)
        end_date: End date of the training period (str or datetime)
    """
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{symbol}.yaml")
    
    # Format dates consistently if they are provided
    if start_date:
        if not isinstance(start_date, str):
            start_date = start_date.strftime('%Y-%m-%d')
    
    if end_date:
        if not isinstance(end_date, str):
            end_date = end_date.strftime('%Y-%m-%d')
    
    # Add metadata section with timestamp and training period
    config = {
        'metadata': {
            'optimization_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'training_period': {
                'start_date': start_date,
                'end_date': end_date
            }
        }
    }
    
    # Add technical indicator parameters
    for indicator, params in best_params.items():
        config[indicator] = params
    
    with open(output_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    logger.info(f"Saved configuration for {symbol} to {output_file}")
    return output_file

def run_stock_grid_search(input_data_path, stock_symbol, output_dir, 
                        max_combinations=100, max_investment=5000, 
                        initial_capital=10000, metric='win_rate',
                        start_date=None, end_date=None,
                        test_months=6):
    """
    Run grid search for a specific stock to find optimal parameters.
    
    Args:
        input_data_path: Path to data CSV file
        stock_symbol: Stock symbol to optimize
        output_dir: Directory for output files
        max_combinations: Maximum parameter combinations to try
        max_investment: Maximum investment per trade
        initial_capital: Initial capital for performance calculation
        metric: Metric to optimize ('win_rate', 'cagr', 'sharpe_ratio')
        start_date: Start date for training data (YYYY-MM-DD)
        end_date: End date for training data (YYYY-MM-DD)
        test_months: Number of months to set aside for testing
        
    Returns:
        Dictionary with best parameters and performance metrics
    """
    logger.info(f"Running grid search for {stock_symbol}")
    
    try:
        # Load data
        df = pd.read_csv(input_data_path, parse_dates=['timestamp'])
        logger.info(f"Loaded data with shape {df.shape}")
        
        # Filter for the specific stock
        stock_data = df[df['symbol'] == stock_symbol].copy()
        if len(stock_data) < 100:
            logger.warning(f"Insufficient data for {stock_symbol} (only {len(stock_data)} rows)")
            return None
            
        logger.info(f"Found {len(stock_data)} rows for {stock_symbol}")
        
        # Sort by timestamp for consistent results
        stock_data.sort_values('timestamp', inplace=True)
        
        # Filter by date range if specified
        filtered_data = stock_data.copy()
        actual_start = filtered_data['timestamp'].min()
        actual_end = filtered_data['timestamp'].max()
        
        if start_date:
            start_date_dt = pd.to_datetime(start_date)
            filtered_data = filtered_data[filtered_data['timestamp'] >= start_date_dt]
            logger.info(f"Filtered data to start from {start_date}")
            
        if end_date:
            end_date_dt = pd.to_datetime(end_date)
            filtered_data = filtered_data[filtered_data['timestamp'] <= end_date_dt]
            logger.info(f"Filtered data to end at {end_date}")
            
        if len(filtered_data) < 100:
            logger.warning(f"Insufficient data after date filtering for {stock_symbol} (only {len(filtered_data)} rows)")
            return None
            
        # Record the actual date range used
        actual_start = filtered_data['timestamp'].min()
        actual_end = filtered_data['timestamp'].max()
        logger.info(f"Training period: {actual_start.strftime('%Y-%m-%d')} to {actual_end.strftime('%Y-%m-%d')}")
        
        # Split data into training and testing sets if test_months > 0
        if test_months > 0:
            # Calculate the cutoff date
            cutoff_date = actual_end - pd.DateOffset(months=test_months)
            
            # Split the data
            train_data = filtered_data[filtered_data['timestamp'] <= cutoff_date].copy()
            test_data = filtered_data[filtered_data['timestamp'] > cutoff_date].copy()
            
            logger.info(f"Split data: {len(train_data)} training rows, {len(test_data)} testing rows")
            logger.info(f"Training period: {train_data['timestamp'].min().strftime('%Y-%m-%d')} to {train_data['timestamp'].max().strftime('%Y-%m-%d')}")
            logger.info(f"Testing period: {test_data['timestamp'].min().strftime('%Y-%m-%d')} to {test_data['timestamp'].max().strftime('%Y-%m-%d')}")
            
            # Use training data for optimization
            data_for_optimization = train_data
            actual_start = data_for_optimization['timestamp'].min()
            actual_end = data_for_optimization['timestamp'].max()
        else:
            # Use all filtered data for optimization
            data_for_optimization = filtered_data
            test_data = None
        
        # Define parameter grid for technical indicators
        param_grid = {
            'rsi': {
                'window': [7, 10, 14, 21],
                'overbought': [65, 70, 75, 80],
                'oversold': [20, 25, 30, 35]
            },
            'macd': {
                'fast_period': [6, 8, 12],
                'slow_period': [18, 24, 26],
                'signal_period': [6, 9, 12]
            },
            'bollinger_bands': {
                'window': [14, 20, 26],
                'num_std_dev': [1.5, 2.0, 2.5]
            },
            'support_resistance': {
                'support_period': [10, 14, 21],
                'resistance_period': [10, 14, 21]
            },
            'atr': {
                'window': [7, 14, 21]
            },
            'ema': {
                'period': [9, 21, 50]
            },
            'risk_management': {
                'stop_loss_atr_multiplier': [1.5, 2.0, 2.5],
                'take_profit_atr_multiplier': [2.0, 3.0, 4.0]
            }
        }
        
        # Generate parameter combinations - but limit to key parameters to avoid explosion
        combinations = []
        for rsi_params in product(*param_grid['rsi'].values()):
            for macd_params in product(*param_grid['macd'].values()):
                for bb_params in product(*param_grid['bollinger_bands'].values()):
                    for sr_params in product(*param_grid['support_resistance'].values()):
                        # Use fixed values for less impactful parameters to avoid combinatorial explosion
                        combo = {
                            'rsi': dict(zip(param_grid['rsi'].keys(), rsi_params)),
                            'macd': dict(zip(param_grid['macd'].keys(), macd_params)),
                            'bollinger_bands': dict(zip(param_grid['bollinger_bands'].keys(), bb_params)),
                            'support_resistance': dict(zip(param_grid['support_resistance'].keys(), sr_params)),
                            'atr': {'window': 14},
                            'ema': {'period': 21},
                            'risk_management': {
                                'stop_loss_atr_multiplier': 2.0,
                                'take_profit_atr_multiplier': 3.0
                            },
                            'columns': {
                                'open': 'open',
                                'high': 'high',
                                'low': 'low',
                                'close': 'close',
                                'volume': 'volume',
                                'timestamp': 'timestamp'
                            }
                        }
                        combinations.append(combo)
        
        # Limit number of combinations if needed
        if len(combinations) > max_combinations:
            logger.info(f"Limiting from {len(combinations)} to {max_combinations} combinations")
            combinations = random.sample(combinations, max_combinations)
        
        # Run grid search
        best_score = -float('inf')
        best_params = None
        best_metrics = None
        
        for i, params in enumerate(combinations):
            logger.info(f"Testing combination {i+1}/{len(combinations)}")
            
            # Create a temporary config file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as tmp_file:
                yaml.dump(params, tmp_file)
                tmp_path = tmp_file.name
            
            try:
                # Calculate indicators with these parameters
                ta = TechnicalAnalysis(config_path=tmp_path)
                data_with_indicators = ta.calculate_all_indicators(data_for_optimization)
                
                # Generate trades
                analyzer = PerformanceAnalyzer(max_investment_per_trade=max_investment)
                trades = analyzer.process_signals(data_with_indicators)
                
                if len(trades) < 5:
                    logger.info(f"Combination {i+1} generated only {len(trades)} trades. Skipping.")
                    continue
                
                # Calculate performance metrics
                metrics = analyzer.calculate_performance_metrics(trades, initial_capital=initial_capital)
                
                # Determine score based on specified metric
                if metric == 'win_rate':
                    score = metrics['win_rate']
                elif metric == 'cagr':
                    score = metrics['cagr']
                elif metric == 'sharpe_ratio':
                    score = metrics['sharpe_ratio']
                else:
                    score = metrics['win_rate']
                
                logger.info(f"Combination {i+1} score ({metric}): {score:.2f}")
                
                # Update best parameters if better score found
                if score > best_score:
                    best_score = score
                    best_params = params
                    best_metrics = metrics
                    logger.info(f"New best score: {best_score:.2f}")
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        
        if best_params:
            # Save best parameters to config file
            config_path = save_stock_config(
                stock_symbol, 
                best_params, 
                output_dir,
                start_date=actual_start,
                end_date=actual_end
            )
            
            # Test best parameters on test data if available
            if test_data is not None and len(test_data) >= 50:
                logger.info(f"Testing best parameters on out-of-sample data")
                
                ta = TechnicalAnalysis(config_path=config_path)
                test_data_with_indicators = ta.calculate_all_indicators(test_data)
                
                analyzer = PerformanceAnalyzer(max_investment_per_trade=max_investment)
                test_trades = analyzer.process_signals(test_data_with_indicators)
                
                if len(test_trades) >= 5:
                    test_metrics = analyzer.calculate_performance_metrics(test_trades, initial_capital=initial_capital)
                    
                    logger.info(f"In-sample {metric}: {best_metrics[metric]:.2f}, Out-of-sample {metric}: {test_metrics[metric]:.2f}")
                    
                    # Add test metrics to the return value
                    best_metrics['test_metrics'] = test_metrics
            
            return {
                'stock': stock_symbol,
                'best_params': best_params,
                'metrics': best_metrics,
                'config_path': config_path,
                'training_period': {
                    'start_date': actual_start.strftime('%Y-%m-%d'),
                    'end_date': actual_end.strftime('%Y-%m-%d')
                }
            }
        else:
            logger.warning(f"No valid parameter combination found for {stock_symbol}")
            return None
    except Exception as e:
        logger.error(f"Error in grid search for {stock_symbol}: {str(e)}")
        return None

def update_trading_config(trading_config_path, stock_symbol, config_path,
                         metrics=None, training_period=None):
    """
    Update the trading configuration file with the stock's optimized parameters.
    
    Args:
        trading_config_path: Path to trading configuration file
        stock_symbol: Stock symbol that was optimized
        config_path: Path to the stock's configuration file
        metrics: Performance metrics from the optimization
        training_period: Dictionary with start_date and end_date of training period
    """
    try:
        # Make the config path relative to the trading config
        config_dir = os.path.dirname(trading_config_path)
        rel_config_path = os.path.relpath(config_path, config_dir)
        
        # Load current trading config
        with open(trading_config_path, 'r') as f:
            trading_config = yaml.safe_load(f)
        
        # Find if the stock is already in the config
        stock_entry = None
        if 'stocks' in trading_config:
            for i, entry in enumerate(trading_config['stocks']):
                if isinstance(entry, dict) and entry.get('symbol') == stock_symbol:
                    stock_entry = entry
                    break
                elif entry == stock_symbol:
                    # Replace string entry with dictionary
                    trading_config['stocks'][i] = {'symbol': stock_symbol}
                    stock_entry = trading_config['stocks'][i]
                    break
        
        # If the stock is not in the config, add it
        if not stock_entry:
            if 'stocks' not in trading_config:
                trading_config['stocks'] = []
            trading_config['stocks'].append({'symbol': stock_symbol})
            stock_entry = trading_config['stocks'][-1]
        
        # Update the stock entry
        stock_entry['config'] = rel_config_path
        
        # Add metadata if provided
        if metrics or training_period:
            if 'optimization' not in stock_entry:
                stock_entry['optimization'] = {}
                
            if metrics:
                stock_entry['optimization']['metrics'] = {
                    'win_rate': metrics.get('win_rate'),
                    'cagr': metrics.get('cagr'),
                    'sharpe_ratio': metrics.get('sharpe_ratio')
                }
                
            if training_period:
                stock_entry['optimization']['training_period'] = training_period
                
            stock_entry['optimization']['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Save updated config
        with open(trading_config_path, 'w') as f:
            yaml.dump(trading_config, f, default_flow_style=False)
            
        logger.info(f"Updated trading config for {stock_symbol} with {rel_config_path}")
        
    except Exception as e:
        logger.error(f"Error updating trading config: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Stock-specific grid search for trading parameters')
    parser.add_argument('--input', required=True, help='Path to input data CSV file')
    parser.add_argument('--output-dir', required=True, help='Directory to save stock configs')
    parser.add_argument('--trading-config', default='config/trading_config.yaml', help='Path to trading configuration file')
    parser.add_argument('--stock', help='Specific stock to optimize (default: optimize all active stocks)')
    parser.add_argument('--max-combinations', type=int, default=100, help='Maximum parameter combinations to try')
    parser.add_argument('--max-investment', type=float, default=5000, help='Maximum investment per trade')
    parser.add_argument('--initial-capital', type=float, default=10000, help='Initial capital')
    parser.add_argument('--metric', choices=['win_rate', 'cagr', 'sharpe_ratio'], default='win_rate', 
                      help='Metric to optimize for')
    parser.add_argument('--start-date', help='Start date for training data (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for training data (YYYY-MM-DD)')
    parser.add_argument('--test-months', type=int, default=6, help='Number of months to set aside for testing')
    parser.add_argument('--metadata-file', help='File to save optimization metadata')
    
    args = parser.parse_args()
    
    try:
        # Create output directory if it doesn't exist
        os.makedirs(args.output_dir, exist_ok=True)
        
        # Load trading config
        with open(args.trading_config, 'r') as f:
            trading_config = yaml.safe_load(f)
        
        # Determine which stocks to optimize
        stocks_to_optimize = []
        
        if args.stock:
            # Optimize only the specified stock
            stocks_to_optimize.append(args.stock)
        else:
            # Optimize all stocks from trading config
            for stock in trading_config.get('stocks', []):
                if isinstance(stock, dict):
                    symbol = stock.get('symbol')
                    if symbol:
                        stocks_to_optimize.append(symbol)
                else:
                    stocks_to_optimize.append(stock)
        
        logger.info(f"Will optimize {len(stocks_to_optimize)} stocks: {', '.join(stocks_to_optimize)}")
        
        # Track optimization results
        optimization_results = {}
        
        # Run grid search for each stock
        for symbol in stocks_to_optimize:
            logger.info(f"Starting optimization for {symbol}")
            
            result = run_stock_grid_search(
                args.input,
                symbol,
                args.output_dir,
                args.max_combinations,
                args.max_investment,
                args.initial_capital,
                args.metric,
                args.start_date,
                args.end_date,
                args.test_months
            )
            
            if result:
                # Update trading config with the best parameters
                update_trading_config(
                    args.trading_config,
                    symbol,
                    result['config_path'],
                    result['metrics'],
                    result['training_period']
                )
                
                # Store results
                optimization_results[symbol] = {
                    'metrics': result['metrics'],
                    'config_path': result['config_path'],
                    'training_period': result['training_period']
                }
        
        # Save metadata about this optimization run if requested
        if args.metadata_file:
            metadata = {
                'optimization_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'parameters': {
                    'input_data': args.input,
                    'max_combinations': args.max_combinations,
                    'metric': args.metric,
                    'start_date': args.start_date,
                    'end_date': args.end_date,
                    'test_months': args.test_months
                },
                'results': optimization_results
            }
            
            with open(args.metadata_file, 'w') as f:
                yaml.dump(metadata, f, default_flow_style=False)
            
            logger.info(f"Saved optimization metadata to {args.metadata_file}")
        
        # Print summary
        print("\nOptimization Summary:")
        for symbol, result in optimization_results.items():
            metrics = result['metrics']
            print(f"{symbol}:")
            print(f"  Win Rate: {metrics['win_rate']:.2f}%")
            print(f"  CAGR: {metrics['cagr']:.2f}%")
            print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            
            if 'test_metrics' in metrics:
                test = metrics['test_metrics']
                print(f"  Out-of-sample Win Rate: {test['win_rate']:.2f}%")
                print(f"  Out-of-sample CAGR: {test['cagr']:.2f}%")
                print(f"  Out-of-sample Sharpe Ratio: {test['sharpe_ratio']:.2f}")
            
            print()
        
        logger.info("Stock-specific optimization completed")
        
    except Exception as e:
        logger.error(f"Error in stock-specific grid search: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 