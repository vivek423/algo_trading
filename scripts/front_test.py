#!/usr/bin/env python3
import os
import yaml
import argparse
import logging
import pandas as pd
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Import necessary components
from technical_analysis import TechnicalAnalysis
from performance_analyzer import PerformanceAnalyzer, load_stock_configs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def load_optimization_metadata(metadata_path: str) -> Dict:
    """Load metadata about a previous optimization run."""
    try:
        with open(metadata_path, 'r') as f:
            metadata = yaml.safe_load(f)
        logger.info(f"Loaded optimization metadata from {metadata_path}")
        return metadata
    except Exception as e:
        logger.error(f"Error loading optimization metadata: {str(e)}")
        raise

def load_testing_data(data_path: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """Load and filter testing data based on date range."""
    try:
        df = pd.read_csv(data_path, parse_dates=['timestamp'])
        logger.info(f"Loaded data from {data_path} with shape {df.shape}")
        
        # Filter by date range if specified
        if start_date or end_date:
            if start_date:
                start_date_dt = pd.to_datetime(start_date)
                df = df[df['timestamp'] >= start_date_dt]
                logger.info(f"Filtered data to start from {start_date}")
            
            if end_date:
                end_date_dt = pd.to_datetime(end_date)
                df = df[df['timestamp'] <= end_date_dt]
                logger.info(f"Filtered data to end at {end_date}")
        
        logger.info(f"Testing data shape after filtering: {df.shape}")
        logger.info(f"Testing data date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        return df
    except Exception as e:
        logger.error(f"Error loading testing data: {str(e)}")
        raise

def process_stock(stock_symbol: str, testing_data: pd.DataFrame, config_path: str, 
                 max_investment: float = 5000) -> List:
    """
    Process a single stock with its optimized parameters for front testing.
    
    Args:
        stock_symbol: Stock symbol to process
        testing_data: DataFrame containing testing data for all stocks
        config_path: Path to the stock's optimized configuration file
        max_investment: Maximum investment per trade
        
    Returns:
        List of trades generated for this stock
    """
    try:
        # Filter testing data for this stock
        stock_data = testing_data[testing_data['symbol'] == stock_symbol].copy()
        
        if len(stock_data) < 10:
            logger.warning(f"Insufficient testing data for {stock_symbol} (only {len(stock_data)} rows). Skipping.")
            return []
        
        logger.info(f"Processing {stock_symbol} with {len(stock_data)} data points using config {config_path}")
        
        # Check if config path exists
        if not os.path.exists(config_path):
            logger.warning(f"Failed to load config from {config_path}: {os.path.basename(config_path)} not found. Falling back to default config.")
            config_path = "config/technical_indicators.yaml"
            
        # Load the stock's optimized configuration
        ta = TechnicalAnalysis(config_path=config_path)
        
        # Load optimization metadata from config
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            if 'metadata' in config:
                training_period = config['metadata'].get('training_period', {})
                optimization_date = config['metadata'].get('optimization_timestamp', 'Unknown')
                logger.info(f"Using parameters optimized on: {optimization_date}")
                logger.info(f"Original training period: {training_period.get('start_date', 'Unknown')} to {training_period.get('end_date', 'Unknown')}")
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            logger.warning(f"Failed to load config from {config_path}: {str(e)}. Falling back to default config.")
            config_path = "config/technical_indicators.yaml"
            ta = TechnicalAnalysis(config_path=config_path)
        
        # Calculate indicators using optimized parameters
        stock_data = ta.calculate_all_indicators(stock_data)
        
        # Initialize performance analyzer
        analyzer = PerformanceAnalyzer(max_investment_per_trade=max_investment)
        
        # Process signals and generate trades
        trades = analyzer.process_signals(stock_data)
        
        logger.info(f"Generated {len(trades)} trades for {stock_symbol} in front testing")
        
        return trades
    except Exception as e:
        logger.error(f"Error processing {stock_symbol}: {str(e)}")
        return []

def run_front_testing(testing_data_path: str, output_dir: str, trading_config_path: str,
                     max_investment: float = 5000, initial_capital: float = 10000,
                     start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict:
    """
    Run front testing on all stocks using previously optimized parameters.
    
    Args:
        testing_data_path: Path to testing data CSV
        output_dir: Directory to save results
        trading_config_path: Path to trading configuration file
        max_investment: Maximum investment per trade
        initial_capital: Initial capital for performance calculation
        start_date: Start date for testing period (YYYY-MM-DD)
        end_date: End date for testing period (YYYY-MM-DD)
        
    Returns:
        Dictionary with performance metrics
    """
    # Load stock configurations from trading config
    stock_configs = load_stock_configs(trading_config_path)
    if not stock_configs:
        raise ValueError("No stock configurations found in trading config")
    
    # Load testing data
    testing_data = load_testing_data(testing_data_path, start_date, end_date)
    
    # Process each stock with its optimized parameters
    all_trades = []
    stock_performance = {}
    
    for symbol, config_path in stock_configs.items():
        trades = process_stock(symbol, testing_data, config_path, max_investment)
        all_trades.extend(trades)
        
        # Calculate per-stock metrics
        if trades:
            analyzer = PerformanceAnalyzer(max_investment_per_trade=max_investment)
            metrics = analyzer.calculate_performance_metrics(trades, initial_capital=initial_capital)
            stock_performance[symbol] = {
                'trades': len(trades),
                'win_rate': metrics['win_rate'],
                'cagr': metrics['cagr'],
                'sharpe_ratio': metrics['sharpe_ratio'],
                'realized_pnl': metrics['realized_pnl'],
                'max_drawdown': metrics['max_drawdown']
            }
    
    # Calculate overall performance metrics
    analyzer = PerformanceAnalyzer(max_investment_per_trade=max_investment)
    overall_metrics = analyzer.calculate_performance_metrics(all_trades, initial_capital=initial_capital)
    
    # Generate yearly summary
    yearly_summary = analyzer.generate_yearly_summary(all_trades, initial_capital=initial_capital)
    
    # Save results
    os.makedirs(output_dir, exist_ok=True)
    
    # Save overall metrics
    with open(os.path.join(output_dir, 'front_test_metrics.yaml'), 'w') as f:
        overall_with_metadata = {
            'test_run_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'testing_period': {
                'start_date': testing_data['timestamp'].min().strftime('%Y-%m-%d'),
                'end_date': testing_data['timestamp'].max().strftime('%Y-%m-%d')
            },
            'metrics': overall_metrics,
            'stock_performance': stock_performance
        }
        yaml.dump(overall_with_metadata, f, default_flow_style=False)
    
    # Save yearly summary
    yearly_summary.to_csv(os.path.join(output_dir, 'front_test_yearly_summary.csv'))
    
    # Save trade log
    if all_trades:
        analyzer = PerformanceAnalyzer(max_investment_per_trade=max_investment)
        sorted_trades = sorted(all_trades, key=lambda t: t.entry_date)
        
        # Prepare for capital allocation tracking
        cash_balance = initial_capital
        additional_capital_needed = []
        capital_after_trade = []
        
        # Process each trade to calculate its capital impact
        for trade in sorted_trades:
            trade_cost = trade.entry_price * trade.quantity
            
            # Check if we need additional capital
            if trade_cost > cash_balance:
                additional_capital = trade_cost - cash_balance
                additional_capital_needed.append(additional_capital)
                cash_balance = 0
            else:
                additional_capital_needed.append(0)
                cash_balance -= trade_cost
            
            # Record cash balance after investment
            capital_after_trade.append(cash_balance)
            
            # When the trade is closed, add proceeds back to cash
            if trade.exit_price and trade.pnl is not None:
                cash_balance += trade.exit_price * trade.quantity
        
        # Save detailed trade log with capital information
        trade_log = pd.DataFrame([
            {
                'symbol': t.symbol,
                'entry_date': t.entry_date,
                'entry_price': t.entry_price,
                'quantity': t.quantity,
                'investment': t.entry_price * t.quantity,
                'additional_capital_needed': add_capital,
                'cash_after_entry': cash_bal,
                'stop_loss': t.stop_loss,
                'take_profit': t.take_profit,
                'exit_date': t.exit_date,
                'exit_price': t.exit_price,
                'exit_reason': t.exit_reason,
                'pnl': t.pnl,
                'return_pct': (t.pnl / (t.entry_price * t.quantity) * 100) if t.pnl is not None else None
            }
            for t, add_capital, cash_bal in zip(sorted_trades, additional_capital_needed, capital_after_trade)
        ])
        trade_log.to_csv(os.path.join(output_dir, 'front_test_trade_log.csv'), index=False)
    
    return overall_metrics, stock_performance

def main():
    parser = argparse.ArgumentParser(description='Run front testing with previously optimized parameters')
    parser.add_argument('--testing-data', required=True, help='Path to testing data CSV file')
    parser.add_argument('--output', required=True, help='Directory to save front testing results')
    parser.add_argument('--trading-config', default='config/trading_config.yaml', help='Path to trading configuration file')
    parser.add_argument('--max-investment', type=float, default=5000, help='Maximum investment per trade')
    parser.add_argument('--initial-capital', type=float, default=10000, help='Initial capital for performance calculation')
    parser.add_argument('--start-date', help='Start date for testing period (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for testing period (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    try:
        # Run front testing
        overall_metrics, stock_performance = run_front_testing(
            args.testing_data,
            args.output,
            args.trading_config,
            args.max_investment,
            args.initial_capital,
            args.start_date,
            args.end_date
        )
        
        # Print summary
        print("\nFront Testing Summary:")
        print(f"Total Trades: {overall_metrics['total_trades']}")
        print(f"Win Rate: {overall_metrics['win_rate']:.2f}%")
        print(f"CAGR: {overall_metrics['cagr']:.2f}%")
        print(f"Sharpe Ratio: {overall_metrics['sharpe_ratio']:.2f}")
        print(f"Initial Capital: ₹{overall_metrics['initial_capital']:,.2f}")
        print(f"Final Capital: ₹{overall_metrics['final_capital']:,.2f}")
        print(f"Realized P&L: ₹{overall_metrics['realized_pnl']:,.2f}")
        print(f"Maximum Drawdown: {overall_metrics['max_drawdown']:.2f}%")
        
        # Print top performing stocks
        print("\nTop Performing Stocks:")
        top_stocks = sorted(stock_performance.items(), key=lambda x: x[1]['realized_pnl'], reverse=True)[:5]
        for symbol, metrics in top_stocks:
            print(f"{symbol}: {metrics['trades']} trades, Win Rate: {metrics['win_rate']:.2f}%, P&L: ₹{metrics['realized_pnl']:,.2f}")
        
        logger.info(f"Front testing completed. Results saved to {args.output}")
        
    except Exception as e:
        logger.error(f"Error in front testing: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 