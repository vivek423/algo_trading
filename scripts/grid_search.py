import pandas as pd
import numpy as np
import yaml
import argparse
from itertools import product
from typing import Dict, List, Tuple, Optional, Union
import logging
from datetime import datetime
import os
import sys
import tempfile
import traceback
import glob
from technical_analysis import TechnicalAnalysis
from performance_analyzer import PerformanceAnalyzer, Trade

def setup_logging(output_dir: str):
    """Set up logging configuration."""
    log_file = os.path.join(output_dir, 'grid_search.log')
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a unique logger for grid search
    logger = logging.getLogger('grid_search')
    logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers
    logger.handlers = []
    
    # Add new handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler(log_file, mode='w')
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger

class GridSearchOptimizer:
    def __init__(self, 
                 data_path: Optional[str] = None, 
                 output_dir: str = "logs/grid_search",
                 max_investment_per_trade: float = 5000, 
                 initial_capital: float = 10000,
                 input_dir: Optional[str] = None,
                 stocks: Optional[List[str]] = None,
                 trading_config: Optional[str] = None):
        """
        Initialize GridSearchOptimizer.
        
        Args:
            data_path: Path to CSV file containing combined OHLC data for all stocks (optional)
            output_dir: Directory to save optimization results
            max_investment_per_trade: Maximum amount to invest per trade
            initial_capital: Initial capital for the portfolio
            input_dir: Directory containing individual stock OHLC data files (alternative to data_path)
            stocks: List of stock symbols to process (if not specified, will process all available)
            trading_config: Path to trading configuration file (to get list of stocks if not specified)
        """
        self.data_path = data_path
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.max_investment = max_investment_per_trade
        self.initial_capital = initial_capital
        self.specific_stocks = stocks
        self.trading_config_path = trading_config
        self.logger = setup_logging(output_dir)
        
        self.logger.info(f"Initializing GridSearchOptimizer")
        self.logger.info(f"Max investment per trade: {max_investment_per_trade}")
        self.logger.info(f"Initial capital: {initial_capital}")
        
        # Setup data source
        if data_path is not None:
            self._load_consolidated_data()
        elif input_dir is not None:
            self._setup_individual_files()
        else:
            raise ValueError("Either data_path or input_dir must be specified")
        
        # Define parameter ranges for grid search
        self.param_ranges = {
            'macd': {
                'fast_period': [8, 12, 16],
                'slow_period': [21, 26, 34],
                'signal_period': [7, 9, 12]
            },
            'support_resistance': {
                'support_period': [10, 15, 20],
                'resistance_period': [10, 15, 20]
            },
            'atr': {
                'window': [10, 14, 21]
            },
            'ema': {
                'period': [10, 15, 20]
            },
            'bollinger_bands': {
                'length': [20, 30, 40],
                'std': [1.8, 2.0, 2.2]
            },
            'rsi': {
                'length': [10, 14, 20],
                'oversold': [25, 30, 35],
                'overbought': [65, 70, 75]
            },
            'risk_management': {
                'stop_loss_atr_multiplier': [1.5, 2.0, 2.5],
                'take_profit_atr_multiplier': [2.0, 2.5, 3.0]
            }
        }
        
        # Default column names
        self.columns = {
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'timestamp': 'timestamp'
        }
        
        self.logger.info(f"Created output directory: {output_dir}")
        
    def _load_consolidated_data(self):
        """Load data from a consolidated CSV file."""
        try:
            self.logger.info(f"Loading consolidated data from {self.data_path}")
            self.data = pd.read_csv(self.data_path)
            self.logger.debug(f"Raw data columns: {self.data.columns.tolist()}")
            
            # Ensure required columns exist
            required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'symbol']
            missing_columns = [col for col in required_columns if col not in self.data.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
            self.data = self.data.sort_values(['symbol', 'timestamp'])
            
            # Get list of stocks
            self.stocks = list(self.data['symbol'].unique())
            if self.specific_stocks:
                self.stocks = [s for s in self.stocks if s in self.specific_stocks]
            
            # Log data info
            self.logger.info(f"Successfully loaded data from {self.data_path}")
            self.logger.info(f"Data shape: {self.data.shape}")
            self.logger.info(f"Number of unique stocks: {len(self.stocks)}")
            self.logger.info(f"Date range: {self.data['timestamp'].min()} to {self.data['timestamp'].max()}")
            self.logger.info(f"Number of unique dates: {len(self.data['timestamp'].unique())}")
            
            self.use_individual_files = False
            
        except Exception as e:
            self.logger.error(f"Error loading data: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def _setup_individual_files(self):
        """Setup for reading from individual stock files."""
        try:
            self.logger.info(f"Using individual stock files from {self.input_dir}")
            
            # Get list of stock files
            file_pattern = os.path.join(self.input_dir, "*_day.csv")  # Assuming daily data
            stock_files = glob.glob(file_pattern)
            
            if not stock_files:
                self.logger.error(f"No stock files found in {self.input_dir}")
                raise ValueError(f"No stock files found in {self.input_dir}")
            
            # Extract stock symbols from filenames
            all_stocks = [os.path.basename(f).split('_')[0] for f in stock_files]
            
            # If specific stocks were provided, filter the list
            if self.specific_stocks:
                self.stocks = [s for s in all_stocks if s in self.specific_stocks]
            # If trading config was provided, load stocks from there
            elif self.trading_config_path:
                with open(self.trading_config_path, 'r') as f:
                    config = yaml.safe_load(f)
                config_stocks = []
                if isinstance(config.get('stocks'), list):
                    # Handle both formats (list of strings or list of dicts)
                    for stock in config['stocks']:
                        if isinstance(stock, dict):
                            if 'symbol' in stock:
                                config_stocks.append(stock['symbol'])
                        else:
                            config_stocks.append(stock)
                self.stocks = [s for s in all_stocks if s in config_stocks]
            else:
                self.stocks = all_stocks
            
            self.logger.info(f"Found {len(stock_files)} stock files")
            self.logger.info(f"Will process {len(self.stocks)} stocks")
            
            # Sample a file to get date range
            sample_file = stock_files[0]
            sample_df = pd.read_csv(sample_file)
            sample_df['timestamp'] = pd.to_datetime(sample_df['timestamp'])
            
            self.logger.info(f"Date range sample: {sample_df['timestamp'].min()} to {sample_df['timestamp'].max()}")
            self.logger.info(f"Number of unique dates sample: {len(sample_df['timestamp'].unique())}")
            
            self.use_individual_files = True
            self.file_map = {os.path.basename(f).split('_')[0]: f for f in stock_files}
            
        except Exception as e:
            self.logger.error(f"Error setting up individual files: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def generate_param_combinations(self) -> List[Dict]:
        """Generate all possible combinations of parameters."""
        param_names = []
        param_values = []
        
        for section, params in self.param_ranges.items():
            for param, values in params.items():
                param_names.append(f"{section}.{param}")
                param_values.append(values)
        
        combinations = []
        for values in product(*param_values):
            config = {}
            for name, value in zip(param_names, values):
                section, param = name.split('.')
                if section not in config:
                    config[section] = {}
                config[section][param] = value
            combinations.append(config)
        
        total_combinations = len(combinations)
        self.logger.info(f"Generated {total_combinations} parameter combinations")
        return combinations
    
    def evaluate_parameters(self, params: Dict) -> Dict:
        """
        Evaluate a set of parameters using performance analyzer framework.
        
        Args:
            params: Dictionary of parameters to evaluate
            
        Returns:
            Dict containing performance metrics
        """
        try:
            # Create a temporary config file with the parameters
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                # Add columns section to the configuration
                config = {**params, 'columns': self.columns}
                yaml.dump(config, f)
                config_path = f.name
            
            self.logger.debug(f"Created temporary config file: {config_path}")
            
            # Initialize TechnicalAnalysis with the temporary config
            ta = TechnicalAnalysis(config_path)
            
            # Process each stock separately, collecting all trades
            all_trades = []
            
            # Log number of stocks being processed
            self.logger.debug(f"Processing {len(self.stocks)} stocks: {self.stocks[:5]}...")
            
            for symbol in self.stocks:
                try:
                    if self.use_individual_files:
                        # Load data from individual file
                        if symbol not in self.file_map:
                            self.logger.debug(f"No file found for {symbol}, skipping")
                            continue
                        
                        file_path = self.file_map[symbol]
                        stock_data = pd.read_csv(file_path)
                        stock_data['symbol'] = symbol  # Add symbol column
                    else:
                        # Filter from consolidated data
                        stock_data = self.data[self.data['symbol'] == symbol].copy()
                    
                    if len(stock_data) < 10:  # Skip stocks with very little data
                        self.logger.debug(f"Skipping {symbol} - insufficient data ({len(stock_data)} rows)")
                        continue
                    
                    # Ensure timestamp is datetime
                    stock_data['timestamp'] = pd.to_datetime(stock_data['timestamp'])
                        
                    # Calculate indicators and generate signals
                    df = ta.calculate_all_indicators(stock_data)
                    
                    # Initialize performance analyzer for signal processing
                    signal_analyzer = PerformanceAnalyzer(max_investment_per_trade=self.max_investment)
                    
                    # Process signals and generate trades
                    trades = signal_analyzer.process_signals(df)
                    
                    if trades:
                        self.logger.debug(f"Generated {len(trades)} trades for {symbol}")
                        all_trades.extend(trades)
                    else:
                        self.logger.debug(f"No trades generated for {symbol}")
                        
                except Exception as e:
                    self.logger.warning(f"Error processing {symbol}: {str(e)}")
                    continue
            
            # Clean up temporary file
            os.unlink(config_path)
            
            if not all_trades:
                self.logger.warning("No trades were generated for any stock")
                return {
                    'num_trades': 0,
                    'win_rate': 0,
                    'cagr': 0,
                    'sharpe_ratio': -999,
                    'max_drawdown': 0,
                    'final_capital': self.initial_capital,
                    'params': params
                }
            
            # Validate trade dates and fix any issues
            for trade in all_trades:
                # Ensure dates are pandas Timestamp objects
                if not isinstance(trade.entry_date, pd.Timestamp):
                    try:
                        trade.entry_date = pd.Timestamp(trade.entry_date)
                    except:
                        self.logger.warning(f"Invalid entry date for {trade.symbol}: {trade.entry_date}")
                
                if trade.exit_date and not isinstance(trade.exit_date, pd.Timestamp):
                    try:
                        trade.exit_date = pd.Timestamp(trade.exit_date)
                    except:
                        self.logger.warning(f"Invalid exit date for {trade.symbol}: {trade.exit_date}")
            
            # Log completed trades
            completed_trades = [t for t in all_trades if t.exit_date is not None and t.pnl is not None]
            self.logger.debug(f"Total trades: {len(all_trades)}, Completed trades: {len(completed_trades)}")
            
            # Check if we have enough completed trades to calculate meaningful metrics
            if len(completed_trades) < 5:  # Arbitrary threshold - adjust as needed
                self.logger.warning(f"Very few completed trades: {len(completed_trades)}. Metrics may be unreliable.")
            
            # Log date range of trades
            if all_trades:
                entry_dates = [t.entry_date for t in all_trades]
                exit_dates = [t.exit_date for t in all_trades if t.exit_date]
                
                self.logger.debug(f"Trade date range: {min(entry_dates)} to {max(exit_dates) if exit_dates else 'now'}")
                self.logger.debug(f"Trade duration (days): {(max(exit_dates) - min(entry_dates)).days if exit_dates else 0}")
            
            # Sample some trade data for debugging
            if completed_trades:
                sample_trade = completed_trades[0]
                self.logger.debug(f"Sample trade: {sample_trade.symbol}, Entry: {sample_trade.entry_date}, Exit: {sample_trade.exit_date}, PnL: {sample_trade.pnl}")
            
            # Calculate overall performance metrics
            analyzer = PerformanceAnalyzer(max_investment_per_trade=self.max_investment)
            metrics = analyzer.calculate_performance_metrics(all_trades, initial_capital=self.initial_capital)
            
            self.logger.debug(f"Raw calculated metrics: CAGR={metrics['cagr']}, Sharpe={metrics['sharpe_ratio']}")
            
            # Format the metrics correctly - avoiding any NaN or infinite values
            result = {
                'parameters': params,
                'total_trades': metrics['total_trades'],
                'win_rate': float(metrics['win_rate']),
                'sharpe_ratio': float(metrics['sharpe_ratio']) if np.isfinite(metrics['sharpe_ratio']) else 0.0,
                'cagr': float(metrics['cagr']) if np.isfinite(metrics['cagr']) else 0.0,
                'max_drawdown': float(metrics['max_drawdown']) if np.isfinite(metrics['max_drawdown']) else 0.0,
                'initial_capital': float(metrics['initial_capital']),
                'max_capital_used': float(metrics['max_capital_used']),
                'additional_capital_required': float(metrics['additional_capital_required']),
                'final_capital': float(metrics['final_capital']),
                'realized_pnl': float(metrics['realized_pnl']),
                'avg_capital_utilization': float(metrics['avg_capital_utilization']) if np.isfinite(metrics['avg_capital_utilization']) else 0.0,
                'max_concurrent_trades': int(metrics['max_concurrent_trades'])
            }
            
            # Log numeric values to check for zeros
            self.logger.debug(f"Final formatted result: trades={result['total_trades']}, sharpe={result['sharpe_ratio']}, cagr={result['cagr']}, final_capital={result['final_capital']}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error evaluating parameters: {str(e)}")
            self.logger.error(f"Parameters that caused error: {params}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def run_grid_search(self, max_combinations: int = None):
        """Run grid search optimization."""
        try:
            combinations = self.generate_param_combinations()
            if max_combinations:
                combinations = combinations[:max_combinations]
                self.logger.info(f"Limited to {max_combinations} combinations")
            
            self.logger.info(f"Starting grid search with {len(combinations)} combinations")
            results = []
            
            for i, params in enumerate(combinations, 1):
                self.logger.info(f"Testing combination {i}/{len(combinations)}")
                result = self.evaluate_parameters(params)
                if result:
                    # Handle the case where no trades are generated
                    if 'total_trades' not in result:
                        self.logger.warning(f"Combination {i} - No trade data available, skipping")
                        continue
                        
                    results.append(result)
                    # Format percentages properly
                    win_rate_pct = result.get('win_rate', 0)
                    cagr_pct = result.get('cagr', 0)
                    trades = result.get('total_trades', 0)
                    pnl = result.get('realized_pnl', 0)
                    sharpe = result.get('sharpe_ratio', 0)
                    
                    self.logger.info(f"Combination {i} - Trades: {trades}, "
                                     f"Win Rate: {win_rate_pct:.2f}%, "
                                     f"Sharpe: {sharpe:.4f}, "
                                     f"CAGR: {cagr_pct:.2f}%, "
                                     f"PnL: {pnl:.2f}")
            
            if not results:
                self.logger.error("No valid results were generated during grid search")
                return None
                
            # Sort results by Sharpe ratio
            results.sort(key=lambda x: x['sharpe_ratio'], reverse=True)
            
            # Save results
            self.save_results(results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in grid search: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def save_results(self, results: List[Dict]):
        """Save grid search results."""
        if not results:
            self.logger.error("No results to save")
            return
            
        # Save top 10 configurations
        top_configs = results[:10]
        configs_file = os.path.join(self.output_dir, 'top_configurations.yaml')
        
        with open(configs_file, 'w') as f:
            yaml.dump(top_configs, f, default_flow_style=False)
        
        # Save all results to CSV
        results_df = pd.DataFrame([
            {
                'sharpe_ratio': r['sharpe_ratio'],
                'total_trades': r['total_trades'],
                'win_rate': r['win_rate'],
                'cagr': r['cagr'],
                'max_drawdown': r['max_drawdown'],
                'initial_capital': r['initial_capital'],
                'max_capital_used': r['max_capital_used'],
                'additional_capital_required': r['additional_capital_required'],
                'final_capital': r['final_capital'],
                'realized_pnl': r['realized_pnl'],
                'avg_capital_utilization': r['avg_capital_utilization'],
                'max_concurrent_trades': r['max_concurrent_trades'],
                **{f"{k}.{param}": v 
                   for k, params in r['parameters'].items() 
                   for param, v in params.items()}
            }
            for r in results
        ])
        
        results_df.to_csv(os.path.join(self.output_dir, 'grid_search_results.csv'), index=False)
        
        # Log summary
        self.logger.info("\nGrid Search Results Summary:")
        self.logger.info(f"Total combinations tested: {len(results)}")
        self.logger.info(f"Best Sharpe Ratio: {results[0]['sharpe_ratio']:.4f}")
        self.logger.info(f"Best Win Rate: {results[0]['win_rate']:.2f}%")
        self.logger.info(f"Best CAGR: {results[0]['cagr']:.2f}%")
        self.logger.info(f"Initial Capital: {results[0]['initial_capital']:.2f}")
        self.logger.info(f"Max Capital Used: {results[0]['max_capital_used']:.2f}")
        self.logger.info(f"Additional Capital Required: {results[0]['additional_capital_required']:.2f}")
        self.logger.info(f"Final Capital: {results[0]['final_capital']:.2f}")
        self.logger.info(f"Avg Capital Utilization: {results[0]['avg_capital_utilization']:.2f}%")
        self.logger.info(f"Max Concurrent Trades: {results[0]['max_concurrent_trades']}")
        self.logger.info(f"Best Parameters: {results[0]['parameters']}")
        self.logger.info(f"Results saved to: {self.output_dir}")

def main():
    """Main function to run grid search for parameter optimization"""
    parser = argparse.ArgumentParser(description='Grid search for stock trading parameters')
    parser.add_argument('--input', type=str, help='Input CSV file with technical indicators')
    parser.add_argument('--input-dir', type=str, help='Directory containing individual stock OHLCV data files')
    parser.add_argument('--max-investment', type=float, default=5000, help='Maximum investment per trade')
    parser.add_argument('--initial-capital', type=float, default=10000, help='Initial capital')
    parser.add_argument('--metric', choices=['sharpe_ratio', 'cagr', 'win_rate', 'total_pnl'], 
                        default='sharpe_ratio', help='Performance metric to optimize')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of stocks to process')
    parser.add_argument('--max-combinations', type=int, default=5000, 
                       help='Maximum number of parameter combinations to test')
    parser.add_argument('--max-processes', type=int, default=None, 
                       help='Maximum number of CPU processes to use (default: use all available)')
    parser.add_argument('--stocks', type=str, nargs='+', help='Specific stock symbols to process')
    parser.add_argument('--trading-config', type=str, help='Path to trading configuration file to get list of stocks')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.input and not args.input_dir:
        logger.error("Either --input or --input-dir must be specified")
        return
    
    # Hardcoded output directory
    output_dir = 'data/outputs/grid_search'
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Determine which method to use
        if args.input:
            # Load from consolidated file
            logger.info(f"Loading input data from {args.input}")
            df = pd.read_csv(args.input)
            
            # Check for required columns
            required_columns = ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"Missing required columns in input data: {missing_columns}")
                return
                
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Get the list of stocks
            all_stocks = df['symbol'].unique()
            
        else:  # Using input_dir
            logger.info(f"Using individual stock files from {args.input_dir}")
            
            # Get list of stock files
            file_pattern = os.path.join(args.input_dir, "*_day.csv")  # Assuming daily data
            stock_files = glob.glob(file_pattern)
            
            # If no files found with *_day.csv, try a broader pattern
            if not stock_files:
                file_pattern = os.path.join(args.input_dir, "*.csv")
                stock_files = glob.glob(file_pattern)
            
            if not stock_files:
                logger.error(f"No stock files found in {args.input_dir}")
                return
            
            # Extract stock symbols from filenames
            all_stocks = [os.path.basename(f).split('_')[0] for f in stock_files]
            logger.info(f"Found {len(stock_files)} stock files")
            
            # Initialize empty DataFrame for combined data
            df = pd.DataFrame()
            
            # Load data from each file
            for stock_file in stock_files:
                symbol = os.path.basename(stock_file).split('_')[0]
                try:
                    stock_df = pd.read_csv(stock_file)
                    
                    # Add symbol column if not present
                    if 'symbol' not in stock_df.columns:
                        stock_df['symbol'] = symbol
                    
                    # Append to combined DataFrame
                    df = pd.concat([df, stock_df], ignore_index=True)
                except Exception as e:
                    logger.error(f"Error loading {stock_file}: {str(e)}")
            
            # Check if we have data
            if df.empty:
                logger.error("No data loaded from stock files")
                return
            
            # Convert timestamp to datetime
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            else:
                logger.error("Missing 'timestamp' column in data")
                return
        
        # Filter stocks if specific stocks were provided
        if args.stocks:
            logger.info(f"Filtering to specified stocks: {args.stocks}")
            stocks = [s for s in all_stocks if s in args.stocks]
        # If trading config was provided, load stocks from there
        elif args.trading_config:
            logger.info(f"Loading stocks from trading config: {args.trading_config}")
            with open(args.trading_config, 'r') as f:
                config = yaml.safe_load(f)
            config_stocks = []
            if isinstance(config.get('stocks'), list):
                # Handle both formats (list of strings or list of dicts)
                for stock in config['stocks']:
                    if isinstance(stock, dict):
                        if 'symbol' in stock:
                            config_stocks.append(stock['symbol'])
                    else:
                        config_stocks.append(stock)
            stocks = [s for s in all_stocks if s in config_stocks]
        else:
            stocks = all_stocks
        
        # Apply limit if specified
        num_stocks = len(stocks)
        logger.info(f"Found {num_stocks} stocks to process")
        
        if args.limit and args.limit < num_stocks:
            logger.info(f"Limiting to {args.limit} stocks")
            stocks = stocks[:args.limit]
        
        # Filter data to only include selected stocks
        df = df[df['symbol'].isin(stocks)]
        
        if df.empty:
            logger.error("No data found for selected stocks")
            return
        
        # Generate parameter grid
        param_grid, parameter_info = generate_parameter_grid()
        num_combinations = len(param_grid)
        logger.info(f"Generated parameter grid with {num_combinations} combinations")
        
        # Limit combinations if needed
        if args.max_combinations and num_combinations > args.max_combinations:
            logger.info(f"Limiting to {args.max_combinations} combinations")
            param_grid = param_grid[:args.max_combinations]
        
        # Run grid search
        results_df = run_grid_search(df, param_grid, args.initial_capital, args.max_investment)
        
        # Calculate combined metrics
        results_df = calculate_metrics(results_df, args.metric)
        
        # Sort by selected metric
        results_df = results_df.sort_values(args.metric, ascending=False)
        
        # Save results
        metrics_file = os.path.join(output_dir, 'grid_search_results.csv')
        results_df.to_csv(metrics_file, index=False)
        logger.info(f"Saved grid search results to {metrics_file}")
        
        # Save top configurations
        top_configs_file = os.path.join(output_dir, 'top_configurations.yaml')
        top_configs = format_configurations(results_df.head(10), parameter_info)
        
        with open(top_configs_file, 'w') as f:
            yaml.dump(top_configs, f, default_flow_style=False)
        logger.info(f"Saved top configurations to {top_configs_file}")
        
        # Print summary of the best config
        print("\nGrid Search Complete!")
        print(f"Best configuration ({args.metric}={results_df.iloc[0][args.metric]:.4f}):")
        for param, value in top_configs[0].items():
            print(f"  {param}: {value}")
        
    except Exception as e:
        logger.error(f"Error in grid search: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    main() 