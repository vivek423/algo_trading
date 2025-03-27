import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
import logging
import sys
from datetime import datetime
import argparse
from dataclasses import dataclass
import yaml
import os
from technical_analysis import TechnicalAnalysis

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'performance_analyzer.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class Trade:
    symbol: str
    entry_date: pd.Timestamp
    entry_price: float
    quantity: int
    stop_loss: float
    take_profit: float
    exit_date: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl: Optional[float] = None

class PerformanceAnalyzer:
    def __init__(self, max_investment_per_trade: float = 5000):
        """
        Initialize Performance Analyzer
        
        Args:
            max_investment_per_trade: Maximum amount to invest per trade
        """
        self.max_investment = max_investment_per_trade
        self.trades: List[Trade] = []
        self.active_trades: Dict[str, Trade] = {}  # symbol -> Trade
        self.cash_balance: float = 0  # Track available cash
        self.initial_capital: float = 0  # Store initial capital
        
    def calculate_quantity(self, price: float) -> int:
        """Calculate quantity of shares to buy based on price and max investment"""
        if price <= 0:
            return 0
        else:
            # Limit by both max investment and available cash
            max_quantity_by_investment = int(min(self.max_investment // price, self.max_investment / price))
            max_quantity_by_cash = int(self.cash_balance / price)
            return min(max_quantity_by_investment, max_quantity_by_cash)
            
    def process_signals(self, df: pd.DataFrame, initial_capital: float = 10000) -> List[Trade]:
        """Process signals and generate trades"""
        # Reset trades list and initialize cash
        self.trades = []
        self.active_trades = {}
        self.cash_balance = initial_capital
        self.initial_capital = initial_capital
        
        logger.info(f"Starting with initial capital: ₹{initial_capital:,.2f}")
        
        # Make sure we have a timestamp index
        if not isinstance(df.index, pd.DatetimeIndex):
            logger.warning(f"DataFrame index is not DatetimeIndex, converting from {type(df.index)}")
            try:
                # Convert to datetime index if needed
                if 'timestamp' in df.columns:
                    # If timestamp is a column, set it as index
                    df = df.set_index('timestamp')
                
                # Try to convert index to datetime
                df.index = pd.to_datetime(df.index)
                logger.debug(f"Converted index to DatetimeIndex: {df.index[0]} to {df.index[-1]}")
            except Exception as e:
                logger.error(f"Failed to convert DataFrame index to DatetimeIndex: {str(e)}")
        
        # Sort by date to ensure proper order
        df = df.sort_index()
        logger.debug(f"Processing signals for dataframe with shape {df.shape}")
        
        # Process all data chronologically rather than by symbol to properly track cash
        # First, create a unified dataframe with proper datetime index
        df = df.reset_index()
        if 'timestamp' not in df.columns:
            df['timestamp'] = df.index
        
        # Sort by date chronologically
        df = df.sort_values('timestamp')
        
        # Process each day's data
        for date, day_data in df.groupby('timestamp'):
            logger.debug(f"Processing data for {date}, cash balance: ₹{self.cash_balance:,.2f}")
            
            # First check for closing trades (stop loss or take profit)
            for symbol, trade in list(self.active_trades.items()):
                # Find this stock's data for the current day, if it exists
                stock_data = day_data[day_data['symbol'] == symbol]
                if not stock_data.empty:
                    row = stock_data.iloc[0]
                    
                    # Check stop loss
                    if row['low'] <= trade.stop_loss:
                        self._close_trade(trade, pd.Timestamp(date), trade.stop_loss, 'stop_loss')
                        continue
                        
                    # Check take profit
                    if row['high'] >= trade.take_profit:
                        self._close_trade(trade, pd.Timestamp(date), trade.take_profit, 'take_profit')
                        continue
            
            # Then check for new entry signals
            for _, row in day_data.iterrows():
                symbol = row['symbol']
                
                if row['signal_combined'] == 1 and symbol not in self.active_trades:
                    # Check if we have data for the next day
                    next_day_data = df[(df['timestamp'] > date) & (df['symbol'] == symbol)]
                    if len(next_day_data) > 0:
                        entry_price = next_day_data.iloc[0]['open']
                        entry_date = pd.Timestamp(next_day_data.iloc[0]['timestamp'])
                        
                        # Calculate quantity based on available cash
                        quantity = self.calculate_quantity(entry_price)
                        trade_cost = entry_price * quantity
                        
                        # Check if we have enough cash and quantity > 0
                        if quantity > 0 and self.cash_balance >= trade_cost:
                            # Create new trade
                            trade = Trade(
                                symbol=symbol,
                                entry_date=entry_date,
                                entry_price=entry_price,
                                quantity=quantity,
                                stop_loss=row['stop_loss'],
                                take_profit=row['take_profit']
                            )
                            
                            # Update cash balance
                            self.cash_balance -= trade_cost
                            
                            # Record the trade
                            self.active_trades[symbol] = trade
                            self.trades.append(trade)
                            
                            logger.debug(f"New trade: {symbol}, Entry date: {entry_date}, Entry price: {entry_price}, Quantity: {quantity}, Cost: ₹{trade_cost:,.2f}, Remaining cash: ₹{self.cash_balance:,.2f}")
                        else:
                            logger.debug(f"Skipped trade for {symbol} at {entry_date}: Insufficient cash (₹{self.cash_balance:,.2f}) for trade cost (₹{trade_cost:,.2f}) or quantity ({quantity}) too low")
            
        # Close any remaining active trades with the last available price
        for symbol, trade in list(self.active_trades.items()):
            if symbol in df['symbol'].values:
                last_data = df[df['symbol'] == symbol].iloc[-1]
                last_date = pd.Timestamp(last_data['timestamp'])
                logger.debug(f"Closing remaining {symbol} trade at {last_date} with price {last_data['close']}")
                self._close_trade(trade, last_date, last_data['close'], 'end_of_period')
            else:
                logger.warning(f"Symbol {symbol} not found in dataframe, using current time for exit")
                self._close_trade(trade, pd.Timestamp.now(), trade.entry_price, 'end_of_period')
            
        logger.info(f"Generated {len(self.trades)} trades, final cash balance: ₹{self.cash_balance:,.2f}")
        return self.trades
        
    def _close_trade(self, trade: Trade, exit_date: pd.Timestamp, exit_price: float, reason: str):
        """Close a trade and calculate P&L"""
        # Ensure exit_date is a proper Timestamp
        if not isinstance(exit_date, pd.Timestamp):
            try:
                exit_date = pd.Timestamp(exit_date)
            except:
                logger.error(f"Failed to convert exit date: {exit_date}, using current time")
                exit_date = pd.Timestamp.now()
        
        trade.exit_date = exit_date
        trade.exit_price = exit_price
        trade.exit_reason = reason
        trade.pnl = (exit_price - trade.entry_price) * trade.quantity
        
        # Update cash balance when closing the trade
        proceeds = exit_price * trade.quantity
        self.cash_balance += proceeds
        
        # Log trade closure for debugging
        logger.debug(f"Closed trade: {trade.symbol}, Entry: {trade.entry_date}, Exit: {exit_date}, PnL: {trade.pnl:,.2f}, Proceeds: ₹{proceeds:,.2f}, New cash balance: ₹{self.cash_balance:,.2f}")
        
        # Remove from active trades
        if trade.symbol in self.active_trades:
            del self.active_trades[trade.symbol]
            
    def calculate_performance_metrics(self, trades: List[Trade], initial_capital: float = 10000, years: Optional[List[int]] = None) -> Dict:
        """Calculate performance metrics for the specified years with realistic capital management"""
        # Store the initial capital
        self.initial_capital = initial_capital
        
        # Filter trades by year if specified
        if years:
            trades = [t for t in trades if t.entry_date.year in years]
            
        if not trades:
            logger.debug("No trades available for metrics calculation")
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "initial_capital": initial_capital,
                "max_capital_used": initial_capital,
                "additional_capital_required": 0,
                "final_capital": initial_capital,
                "realized_pnl": 0,
                "unrealized_pnl": 0,
                "max_drawdown": 0,
                "sharpe_ratio": 0,
                "cagr": 0,
                "avg_trade_duration": 0,
                "avg_capital_utilization": 0,
                "max_concurrent_trades": 0
            }
        
        # Sort trades chronologically for cash flow analysis
        sorted_trades = sorted(trades, key=lambda t: t.entry_date)
        logger.debug(f"Processing {len(trades)} trades for metrics calculation")
        
        # Calculate basic metrics
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.pnl and t.pnl > 0])
        losing_trades = len([t for t in trades if t.pnl and t.pnl < 0])
        completed_trades = [t for t in trades if t.pnl is not None]
        
        logger.debug(f"Basic metrics: total={total_trades}, winning={winning_trades}, losing={losing_trades}, completed={len(completed_trades)}")
        
        # Calculate realistic capital usage with cash balance tracking
        # Reset cash for metrics calculation
        self.cash_balance = initial_capital
        max_capital_used = initial_capital
        total_additional_capital = 0
        capital_utilization = []  # Track % of capital deployed over time
        concurrent_trades = {}    # Track open trades by date
        max_concurrent = 0        # Track maximum concurrent trades
        
        # Process each trade chronologically
        for trade in sorted_trades:
            # Cost of this trade
            trade_cost = trade.entry_price * trade.quantity
            
            # Check if we need additional capital
            if trade_cost > self.cash_balance:
                additional_capital = trade_cost - self.cash_balance
                total_additional_capital += additional_capital
                self.cash_balance = 0  # We used all available cash
            else:
                self.cash_balance -= trade_cost  # Just use available cash
            
            # Track trade in concurrent trades dictionary
            entry_date_str = trade.entry_date.strftime('%Y-%m-%d')
            if entry_date_str not in concurrent_trades:
                concurrent_trades[entry_date_str] = 0
            concurrent_trades[entry_date_str] += 1
            
            # When the trade is closed, add proceeds back to cash
            if trade.exit_date and trade.exit_price:
                exit_date_str = trade.exit_date.strftime('%Y-%m-%d')
                sale_proceeds = trade.exit_price * trade.quantity
                self.cash_balance += sale_proceeds
                
                # Update concurrent trades on exit
                if exit_date_str not in concurrent_trades:
                    concurrent_trades[exit_date_str] = 0
                concurrent_trades[exit_date_str] -= 1
            
            # Track capital utilization for this day
            current_capital_used = initial_capital + total_additional_capital - self.cash_balance
            capital_utilization.append(current_capital_used / (initial_capital + total_additional_capital))
            
            # Track maximum capital used
            max_capital_used = max(max_capital_used, current_capital_used)
        
        # Calculate maximum concurrent trades
        running_count = 0
        max_concurrent = 0
        
        # Create a timeline of trade events for better accuracy
        entry_events = [(t.entry_date, 1) for t in sorted_trades]
        exit_events = [(t.exit_date, -1) for t in sorted_trades if t.exit_date]
        all_events = sorted(entry_events + exit_events, key=lambda x: x[0])
        
        for date, event in all_events:
            running_count += event
            max_concurrent = max(max_concurrent, running_count)
        
        logger.debug(f"Maximum concurrent trades: {max_concurrent}")
        
        # Calculate average capital utilization
        if capital_utilization:
            avg_capital_util = sum(capital_utilization) / len(capital_utilization) * 100
            # Ensure we don't have negative utilization
            avg_capital_util = max(0, avg_capital_util)
        else:
            avg_capital_util = 0
        
        # Calculate investment and returns using realistic capital measures
        total_investment = max_capital_used  # True total investment is max capital used
        realized_pnl = sum(t.pnl for t in trades if t.pnl is not None)
        unrealized_pnl = sum(t.pnl for t in trades if t.pnl is None)
        
        logger.debug(f"Capital metrics: initial={initial_capital}, max_used={max_capital_used}, realized_pnl={realized_pnl}")
        
        # Calculate final capital
        final_capital = initial_capital + realized_pnl + unrealized_pnl
        
        # Calculate daily returns for Sharpe ratio
        daily_returns = []
        
        logger.debug("Calculating daily returns for Sharpe ratio...")
        for i, trade in enumerate(trades):
            if trade.exit_date and trade.pnl is not None:
                try:
                    days = (trade.exit_date - trade.entry_date).days
                    if days > 0:
                        daily_return = (trade.pnl / (trade.entry_price * trade.quantity)) / days
                        daily_returns.extend([daily_return] * days)
                        if i < 5:  # Log a few example calculations
                            logger.debug(f"  Trade {i}: entry={trade.entry_date}, exit={trade.exit_date}, days={days}, pnl={trade.pnl}, cost={trade.entry_price * trade.quantity}, daily_return={daily_return}")
                    else:
                        logger.debug(f"  Trade {i}: Skipped - Duration is 0 days")
                except Exception as e:
                    logger.warning(f"Error calculating daily return for trade {i}: {str(e)}")
        
        logger.debug(f"Generated {len(daily_returns)} daily return data points")
        
        # Calculate Sharpe ratio - using absolute returns because daily returns are problematic
        if trades and completed_trades:
            try:
                # Calculate absolute returns of each trade (percentage)
                absolute_returns = []
                for trade in completed_trades:
                    if trade.pnl is not None:
                        cost = trade.entry_price * trade.quantity
                        if cost > 0:
                            return_pct = (trade.pnl / cost)
                            absolute_returns.append(return_pct)
                
                if absolute_returns:
                    # Calculate mean return and standard deviation
                    mean_return = np.mean(absolute_returns)
                    std_return = np.std(absolute_returns) if len(absolute_returns) > 1 else 0.01  # Use 1% if only one trade
                    
                    # Use risk-free rate of 4% for the entire trading period
                    risk_free_rate = 0.04
                    
                    logger.debug(f"Absolute returns stats: count={len(absolute_returns)}, mean={mean_return:.4f}, std={std_return:.4f}")
                    
                    if std_return > 0:
                        sharpe_ratio = (mean_return - risk_free_rate) / std_return
                        
                        # Validate the Sharpe ratio is reasonable
                        if not np.isfinite(sharpe_ratio) or abs(sharpe_ratio) > 10:
                            logger.warning(f"Extreme Sharpe ratio detected: {sharpe_ratio}, capping to reasonable range")
                            sharpe_ratio = max(min(sharpe_ratio, 10), -10)  # Cap between -10 and 10
                    else:
                        sharpe_ratio = 0
                        logger.debug("Standard deviation is 0, setting Sharpe ratio to 0")
                else:
                    sharpe_ratio = 0
                    logger.debug("No returns available for Sharpe ratio calculation")
            except Exception as e:
                logger.warning(f"Error calculating Sharpe ratio: {str(e)}")
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
            logger.debug("No trades or completed trades available, setting Sharpe ratio to 0")
            
        logger.debug(f"Calculated Sharpe ratio: {sharpe_ratio}")
            
        # Calculate average trade duration
        durations = []
        for trade in trades:
            if trade.exit_date and trade.entry_date:
                # Ensure both dates are pandas Timestamps
                entry = pd.Timestamp(trade.entry_date)
                exit = pd.Timestamp(trade.exit_date)
                
                # Calculate days between dates
                days = max(1, (exit - entry).days)  # Ensure at least 1 day
                durations.append(days)
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        logger.debug(f"Average trade duration: {avg_duration:.2f} days from {len(durations)} completed trades")
        
        # Calculate CAGR based on initial capital to final capital
        if trades and completed_trades:
            try:
                # Use the earliest entry date and latest exit date to calculate total period
                start_date = min([pd.Timestamp(t.entry_date) for t in trades if t.entry_date])
                
                # For exit dates, use the latest exit date available or now for open trades
                exit_dates = [pd.Timestamp(t.exit_date) for t in completed_trades if t.exit_date]
                if not exit_dates:
                    end_date = pd.Timestamp.now()
                else:
                    end_date = max(exit_dates)
                
                # Ensure end_date is after start_date
                if end_date <= start_date:
                    end_date = start_date + pd.Timedelta(days=30)  # Add a month if dates are problematic
                    logger.warning(f"Fixed invalid date range: start={start_date}, end={end_date}")
                
                years_passed = max(0.1, (end_date - start_date).days / 365.25)  # Ensure at least 0.1 years
                
                logger.debug(f"CAGR calculation: start_date={start_date}, end_date={end_date}, years_passed={years_passed:.2f}")
                logger.debug(f"CAGR inputs: initial_capital={initial_capital}, final_capital={final_capital}")
                
                if final_capital <= 0 or initial_capital <= 0:
                    logger.warning(f"Invalid capital values for CAGR: initial={initial_capital}, final={final_capital}")
                    cagr = 0
                else:
                    # Calculate CAGR using initial to final capital
                    cagr = ((final_capital / initial_capital) ** (1/years_passed) - 1) * 100
                    logger.debug(f"CAGR calculation: ({final_capital:.2f}/{initial_capital:.2f})^(1/{years_passed:.2f}) - 1 = {cagr:.2f}%")
                    
                    # Cap CAGR to reasonable values
                    if not np.isfinite(cagr) or abs(cagr) > 1000:
                        logger.warning(f"Extreme CAGR value: {cagr}, capping to reasonable range")
                        cagr = max(min(cagr, 1000), -100)  # Cap between -100% and 1000%
            except Exception as e:
                logger.warning(f"Error calculating CAGR: {str(e)}")
                cagr = 0
        else:
            cagr = 0
            logger.debug("No completed trades available, setting CAGR to 0")
            
        # Calculate maximum drawdown on portfolio value
        cumulative_returns = []
        portfolio_value = initial_capital
        
        for trade in sorted(trades, key=lambda x: x.entry_date):
            if trade.pnl is not None:
                portfolio_value += trade.pnl
                cumulative_returns.append(portfolio_value)
                
        if cumulative_returns:
            peak = cumulative_returns[0]
            max_drawdown = 0
            
            for value in cumulative_returns:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak
                max_drawdown = max(max_drawdown, drawdown)
        else:
            max_drawdown = 0
            
        # Calculate win rate (ensure it's between 0 and 100)
        completed_trade_count = len(completed_trades)
        win_rate = (winning_trades / completed_trade_count * 100) if completed_trade_count > 0 else 0
        
        # Log final metrics
        logger.debug(f"Final metrics: win_rate={win_rate}, sharpe={sharpe_ratio}, cagr={cagr}, max_drawdown={max_drawdown * 100}")
            
        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "initial_capital": initial_capital,
            "max_capital_used": max_capital_used,
            "additional_capital_required": total_additional_capital,
            "final_capital": final_capital,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "max_drawdown": max_drawdown * 100,  # Convert to percentage
            "sharpe_ratio": sharpe_ratio,
            "cagr": cagr,
            "avg_trade_duration": avg_duration,
            "avg_capital_utilization": avg_capital_util,
            "max_concurrent_trades": max_concurrent
        }
        
    def generate_yearly_summary(self, trades: List[Trade], initial_capital: float = 10000) -> pd.DataFrame:
        """Generate yearly performance summary."""
        if not trades:
            return pd.DataFrame(columns=[
                'year', 'total_trades', 'win_rate', 'realized_pnl', 'cagr',
                'sharpe_ratio', 'max_drawdown', 'avg_trade_duration'
            ])
            
        # Group trades by entry year
        yearly_trades = {}
        for trade in trades:
            year = trade.entry_date.year
            if year not in yearly_trades:
                yearly_trades[year] = []
            yearly_trades[year].append(trade)
        
        # Generate summary for each year
        yearly_summary = []
        for year, year_trades in yearly_trades.items():
            metrics = self.calculate_performance_metrics(year_trades, initial_capital)
            yearly_summary.append({
                'year': year,
                'total_trades': metrics['total_trades'],
                'win_rate': metrics['win_rate'],
                'realized_pnl': metrics['realized_pnl'],
                'cagr': metrics['cagr'],
                'sharpe_ratio': metrics['sharpe_ratio'],
                'max_drawdown': metrics['max_drawdown'],
                'avg_trade_duration': metrics['avg_trade_duration']
            })
        
        # Sort by year
        return pd.DataFrame(yearly_summary).sort_values('year')
        
    def create_trade_log(self, trades: List[Trade]) -> pd.DataFrame:
        """Create a DataFrame with detailed trade log information.
        
        Args:
            trades: List of Trade objects
            
        Returns:
            pd.DataFrame: DataFrame with trade details
        """
        if not trades:
            return pd.DataFrame(columns=[
                'symbol', 'entry_date', 'entry_price', 'quantity', 'investment',
                'stop_loss', 'take_profit', 'exit_date', 'exit_price', 'exit_reason',
                'pnl', 'return_pct', 'duration_days', 'available_cash'
            ])
        
        # Sort trades chronologically by entry date
        sorted_trades = sorted(trades, key=lambda t: t.entry_date)
        
        # Convert trades to dictionary records
        trade_records = []
        
        # Reset cash balance for tracking in trade log
        cash_balance = self.initial_capital
        
        for trade in sorted_trades:
            # Calculate basic metrics
            investment = trade.entry_price * trade.quantity
            
            # Update cash balance for this trade entry
            cash_balance -= investment
            available_cash_after_entry = cash_balance
            
            # Calculate return percentage
            return_pct = 0
            if trade.pnl is not None and investment > 0:
                return_pct = (trade.pnl / investment) * 100
            
            # Calculate duration in days
            duration_days = 0
            if trade.exit_date is not None:
                duration_days = (trade.exit_date - trade.entry_date).days
            
            # Calculate cash after exit (if trade is closed)
            if trade.exit_date is not None and trade.exit_price is not None:
                proceeds = trade.exit_price * trade.quantity
                cash_balance += proceeds
            
            # Create record
            trade_record = {
                'symbol': trade.symbol,
                'entry_date': trade.entry_date,
                'entry_price': trade.entry_price,
                'quantity': trade.quantity,
                'investment': investment,
                'stop_loss': trade.stop_loss,
                'take_profit': trade.take_profit,
                'exit_date': trade.exit_date,
                'exit_price': trade.exit_price,
                'exit_reason': trade.exit_reason,
                'pnl': trade.pnl,
                'return_pct': return_pct,
                'duration_days': duration_days,
                'available_cash': available_cash_after_entry
            }
            
            trade_records.append(trade_record)
        
        return pd.DataFrame(trade_records)

def load_stock_configs(trading_config_path: str) -> Dict[str, str]:
    """
    Load stock-specific configuration paths from trading config.
    
    Args:
        trading_config_path: Path to trading configuration file
        
    Returns:
        Dictionary mapping stock symbols to their config paths
    """
    try:
        with open(trading_config_path, 'r') as f:
            trading_config = yaml.safe_load(f)
            
        # Check if trading config has the new format
        stock_configs = {}
        if trading_config['stocks'] and isinstance(trading_config['stocks'][0], dict):
            for stock_entry in trading_config['stocks']:
                if 'symbol' in stock_entry and 'config' in stock_entry:
                    stock_configs[stock_entry['symbol']] = stock_entry['config']
        
        logger.info(f"Loaded {len(stock_configs)} stock-specific configurations")
        return stock_configs
        
    except Exception as e:
        logger.error(f"Error loading stock configurations: {str(e)}")
        return {}

def main():
    """Run performance analysis"""
    parser = argparse.ArgumentParser(description='Analyze trading performance')
    parser.add_argument('--input', type=str, required=True, help='Input file with technical indicators')
    parser.add_argument('--initial-capital', type=float, default=10000, help='Initial capital for trading')
    parser.add_argument('--max-investment', type=float, default=5000, help='Maximum investment per trade')
    parser.add_argument('--use-stock-configs', action='store_true', help='Use stock-specific configurations')
    parser.add_argument('--metric', choices=['sharpe_ratio', 'cagr', 'win_rate', 'total_pnl'], 
                        default='sharpe_ratio', help='Performance metric to optimize')
    
    args = parser.parse_args()
    
    # Hardcoded output directory
    output_dir = 'data/outputs/performance'
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Load the CSV with technical indicators
        logger.info(f"Loading data from {args.input}")
        df = pd.read_csv(args.input)
        
        logger.info(f"Loaded data with shape {df.shape}")
        unique_symbols = df['symbol'].unique()
        logger.info(f"Found {len(unique_symbols)} symbols in the dataset")
        
        # Initialize performance analyzer
        analyzer = PerformanceAnalyzer(max_investment_per_trade=args.max_investment)
        logger.info(f"Starting with initial capital: ₹{args.initial_capital:,.2f}")
        
        # Process signals to generate trades
        trades = analyzer.process_signals(df, initial_capital=args.initial_capital)
        
        # Calculate performance metrics
        metrics = analyzer.calculate_performance_metrics(trades, initial_capital=args.initial_capital)
        logger.info(f"Total trades across all stocks: {len(trades)}")
        
        # Print the overall metrics summary
        print("\nOverall Performance Summary:")
        for key, value in metrics.items():
            if isinstance(value, float):
                if key in ['cagr', 'win_rate', 'max_drawdown', 'avg_capital_utilization']:
                    print(f"{key.replace('_', ' ').title()}: {value:.2f}%")
                else:
                    print(f"{key.replace('_', ' ').title()}: ₹{value:,.2f}")
            else:
                print(f"{key.replace('_', ' ').title()}: {value}")
        
        # Save the metrics to a YAML file
        metrics_file = os.path.join(output_dir, 'overall_metrics.yaml')
        with open(metrics_file, 'w') as f:
            yaml.dump(metrics, f, default_flow_style=False)
            
        # Generate yearly summary
        yearly_summary = analyzer.generate_yearly_summary(trades, initial_capital=args.initial_capital)
        yearly_file = os.path.join(output_dir, 'yearly_summary.csv')
        yearly_summary.to_csv(yearly_file, index=False)
        
        # Save trade log
        trade_df = analyzer.create_trade_log(trades)
        trade_log_file = os.path.join(output_dir, 'trade_log.csv')
        trade_df.to_csv(trade_log_file, index=False)
        
        logger.info(f"Analysis complete. Reports saved to {output_dir}")
        
    except Exception as e:
        logger.error(f"Error in performance analysis: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise

if __name__ == '__main__':
    main() 