import pandas as pd
import numpy as np
import yaml
import argparse
from itertools import product
from typing import Dict, List, Tuple
import logging
from datetime import datetime
import os
import sys
import tempfile
import traceback
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
    def __init__(self, data_path: str, output_dir: str, max_investment_per_trade: float = 5000, initial_capital: float = 10000):
        """
        Initialize GridSearchOptimizer.
        
        Args:
            data_path: Path to CSV file containing combined OHLC data for all stocks
            output_dir: Directory to save optimization results
            max_investment_per_trade: Maximum amount to invest per trade
            initial_capital: Initial capital for the portfolio
        """
        self.data_path = data_path
        self.output_dir = output_dir
        self.max_investment = max_investment_per_trade
        self.initial_capital = initial_capital
        self.logger = setup_logging(output_dir)
        
        self.logger.info(f"Initializing GridSearchOptimizer with data from {data_path}")
        self.logger.info(f"Max investment per trade: {max_investment_per_trade}")
        self.logger.info(f"Initial capital: {initial_capital}")
        
        # Load and validate data
        try:
            self.data = pd.read_csv(data_path)
            self.logger.debug(f"Raw data columns: {self.data.columns.tolist()}")
            self.logger.debug(f"Raw data sample:\n{self.data.head()}")
            
            # Ensure required columns exist
            required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'symbol']
            missing_columns = [col for col in required_columns if col not in self.data.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
            self.data = self.data.sort_values(['symbol', 'timestamp'])
            
            # Log data info
            self.logger.info(f"Successfully loaded data from {data_path}")
            self.logger.info(f"Data shape: {self.data.shape}")
            self.logger.info(f"Number of unique stocks: {len(self.data['symbol'].unique())}")
            self.logger.info(f"Date range: {self.data['timestamp'].min()} to {self.data['timestamp'].max()}")
            self.logger.info(f"Number of unique dates: {len(self.data['timestamp'].unique())}")
            
        except Exception as e:
            self.logger.error(f"Error loading data: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        
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
            stocks = list(self.data['symbol'].unique())
            self.logger.debug(f"Processing {len(stocks)} stocks: {stocks[:5]}...")
            
            for symbol in stocks:
                stock_data = self.data[self.data['symbol'] == symbol].copy()
                
                if len(stock_data) < 10:  # Skip stocks with very little data
                    self.logger.debug(f"Skipping {symbol} - insufficient data ({len(stock_data)} rows)")
                    continue
                    
                # Calculate indicators and generate signals
                try:
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
                    'parameters': params,
                    'total_trades': 0,
                    'win_rate': 0,
                    'sharpe_ratio': 0,
                    'cagr': 0,
                    'max_drawdown': 0,
                    'initial_capital': self.initial_capital,
                    'max_capital_used': 0,
                    'additional_capital_required': 0,
                    'final_capital': self.initial_capital,
                    'realized_pnl': 0,
                    'avg_capital_utilization': 0,
                    'max_concurrent_trades': 0
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
                    results.append(result)
                    # Format percentages properly
                    win_rate_pct = result['win_rate']
                    cagr_pct = result['cagr']
                    self.logger.info(f"Combination {i} - Trades: {result['total_trades']}, "
                                     f"Win Rate: {win_rate_pct:.2f}%, "
                                     f"Sharpe: {result['sharpe_ratio']:.4f}, "
                                     f"CAGR: {cagr_pct:.2f}%, "
                                     f"PnL: {result['realized_pnl']:.2f}")
            
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
    parser = argparse.ArgumentParser(description='Run grid search optimization for technical indicators')
    parser.add_argument('--input', required=True, help='Path to input CSV file with combined OHLC data for all stocks')
    parser.add_argument('--output', required=True, help='Directory to save results')
    parser.add_argument('--max-combinations', type=int, help='Maximum number of combinations to test')
    parser.add_argument('--max-investment', type=float, default=5000, help='Maximum investment per trade')
    parser.add_argument('--initial-capital', type=float, default=10000, help='Initial capital for portfolio')
    
    args = parser.parse_args()
    
    try:
        optimizer = GridSearchOptimizer(args.input, args.output, args.max_investment, args.initial_capital)
        optimizer.run_grid_search(args.max_combinations)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 