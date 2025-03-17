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
        
    def calculate_quantity(self, price: float) -> int:
        """Calculate quantity of shares to buy based on price and max investment"""
        if price > 5000 and price < 15000:
            return 1
        elif price >= 15000:
            return 0
        else:
            return int(min(self.max_investment // price, self.max_investment / price))
            
    def process_signals(self, df: pd.DataFrame) -> List[Trade]:
        """Process signals and generate trades"""
        # Reset trades list
        self.trades = []
        self.active_trades = {}
        
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
        
        # Group by symbol to process each stock separately
        for symbol, stock_data in df.groupby('symbol'):
            logger.debug(f"Processing signals for {symbol} with {len(stock_data)} data points")
            self._process_stock_signals(symbol, stock_data)
            
        # Close any remaining active trades with the last available price
        for symbol, trade in list(self.active_trades.items()):
            if symbol in df['symbol'].values:
                last_data = df[df['symbol'] == symbol].iloc[-1]
                last_date = pd.Timestamp(last_data.name)
                logger.debug(f"Closing remaining {symbol} trade at {last_date} with price {last_data['close']}")
                self._close_trade(trade, last_date, last_data['close'], 'end_of_period')
            else:
                logger.warning(f"Symbol {symbol} not found in dataframe, using current time for exit")
                self._close_trade(trade, pd.Timestamp.now(), trade.entry_price, 'end_of_period')
            
        logger.debug(f"Generated {len(self.trades)} trades")
        return self.trades
        
    def _process_stock_signals(self, symbol: str, stock_data: pd.DataFrame):
        """Process signals for a single stock"""
        for date, row in stock_data.iterrows():
            # First check if we need to close any active trade
            if symbol in self.active_trades:
                trade = self.active_trades[symbol]
                
                # Check stop loss
                if row['low'] <= trade.stop_loss:
                    self._close_trade(trade, pd.Timestamp(date), trade.stop_loss, 'stop_loss')
                    continue
                    
                # Check take profit
                if row['high'] >= trade.take_profit:
                    self._close_trade(trade, pd.Timestamp(date), trade.take_profit, 'take_profit')
                    continue
            
            # Then check for new entry signals
            if row['signal_combined'] == 1 and symbol not in self.active_trades:
                # Get next day's opening price if available
                next_day_data = stock_data[stock_data.index > date]
                if len(next_day_data) > 0:
                    entry_price = next_day_data.iloc[0]['open']
                    
                    # Ensure the date is a proper pandas Timestamp
                    if isinstance(date, pd.Timestamp):
                        entry_date = pd.Timestamp(next_day_data.index[0])
                    else:
                        logger.warning(f"Date {date} is not a Timestamp, converting from {type(date)}")
                        try:
                            # Try to convert the index to proper timestamp
                            entry_date = pd.Timestamp(next_day_data.index[0])
                        except:
                            logger.error(f"Failed to convert date: {next_day_data.index[0]}")
                            continue
                    
                    # Calculate quantity
                    quantity = self.calculate_quantity(entry_price)
                    
                    if quantity > 0:
                        # Create new trade
                        trade = Trade(
                            symbol=symbol,
                            entry_date=entry_date,
                            entry_price=entry_price,
                            quantity=quantity,
                            stop_loss=row['stop_loss'],
                            take_profit=row['take_profit']
                        )
                        self.active_trades[symbol] = trade
                        self.trades.append(trade)
                        logger.debug(f"New trade: {symbol}, Entry date: {entry_date}, Entry price: {entry_price}")
                        
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
        
        # Log trade closure for debugging
        logger.debug(f"Closed trade: {trade.symbol}, Entry: {trade.entry_date}, Exit: {exit_date}, PnL: {trade.pnl}")
        
        # Remove from active trades
        if trade.symbol in self.active_trades:
            del self.active_trades[trade.symbol]
            
    def calculate_performance_metrics(self, trades: List[Trade], initial_capital: float = 10000, years: Optional[List[int]] = None) -> Dict:
        """Calculate performance metrics for the specified years with realistic capital management"""
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
        cash_balance = initial_capital
        max_capital_used = initial_capital
        additional_capital_needed = 0
        total_additional_capital = 0
        capital_utilization = []  # Track % of capital deployed over time
        concurrent_trades = {}    # Track open trades by date
        max_concurrent = 0        # Track maximum concurrent trades
        
        # Process each trade chronologically
        for trade in sorted_trades:
            # Cost of this trade
            trade_cost = trade.entry_price * trade.quantity
            
            # Check if we need additional capital
            if trade_cost > cash_balance:
                additional_capital = trade_cost - cash_balance
                total_additional_capital += additional_capital
                cash_balance = 0  # We used all available cash
            else:
                cash_balance -= trade_cost  # Just use available cash
            
            # Track trade in concurrent trades dictionary
            entry_date_str = trade.entry_date.strftime('%Y-%m-%d')
            if entry_date_str not in concurrent_trades:
                concurrent_trades[entry_date_str] = 0
            concurrent_trades[entry_date_str] += 1
            
            # When the trade is closed, add proceeds back to cash
            if trade.exit_date and trade.exit_price:
                exit_date_str = trade.exit_date.strftime('%Y-%m-%d')
                sale_proceeds = trade.exit_price * trade.quantity
                cash_balance += sale_proceeds
                
                # Update concurrent trades on exit
                if exit_date_str not in concurrent_trades:
                    concurrent_trades[exit_date_str] = 0
                concurrent_trades[exit_date_str] -= 1
            
            # Track capital utilization for this day
            current_capital_used = initial_capital + total_additional_capital - cash_balance
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
        """Generate yearly summary of performance"""
        yearly_metrics = {}
        
        for year in sorted(set(t.entry_date.year for t in trades)):
            metrics = self.calculate_performance_metrics(trades, initial_capital=initial_capital, years=[year])
            yearly_metrics[year] = metrics
            
        return pd.DataFrame.from_dict(yearly_metrics, orient='index')
        
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
    parser = argparse.ArgumentParser(description='Analyze trading performance')
    parser.add_argument('--input', '-i', required=True, help='Path to input CSV file with technical indicators')
    parser.add_argument('--output', '-o', required=True, help='Path to output directory for reports')
    parser.add_argument('--years', '-y', nargs='+', type=int, help='List of years to analyze')
    parser.add_argument('--max-investment', '-m', type=float, default=5000, help='Maximum investment per trade')
    parser.add_argument('--initial-capital', '-c', type=float, default=10000, help='Initial capital for portfolio')
    parser.add_argument('--trading-config', '-t', default='config/trading_config.yaml', help='Path to trading configuration')
    parser.add_argument('--use-stock-configs', '-s', action='store_true', help='Use stock-specific configurations')
    
    args = parser.parse_args()
    
    try:
        # Load data
        df = pd.read_csv(args.input, parse_dates=['timestamp'], index_col='timestamp')
        
        # Load stock-specific configurations if enabled
        stock_configs = {}
        if args.use_stock_configs:
            stock_configs = load_stock_configs(args.trading_config)
            
        # Process by stock, with stock-specific configs if available
        all_trades = []
        
        # Group by symbol and process each stock separately
        for symbol, stock_data in df.groupby('symbol'):
            logger.info(f"Processing {symbol} with {len(stock_data)} data points")
            
            # Use stock-specific config if available
            config_path = stock_configs.get(symbol) if args.use_stock_configs else None
            
            # If a stock-specific config is available, use it to recalculate indicators
            if config_path and os.path.exists(config_path):
                logger.info(f"Using stock-specific configuration for {symbol}: {config_path}")
                
                # Initialize technical analysis with stock config
                ta = TechnicalAnalysis(config_path=config_path)
                
                # Recalculate indicators using stock-specific parameters
                stock_data = ta.calculate_all_indicators(stock_data)
            
            # Initialize performance analyzer for this stock
            analyzer = PerformanceAnalyzer(max_investment_per_trade=args.max_investment)
            
            # Process signals and generate trades
            stock_trades = analyzer.process_signals(stock_data)
            all_trades.extend(stock_trades)
            
            logger.info(f"Generated {len(stock_trades)} trades for {symbol}")
        
        logger.info(f"Total trades across all stocks: {len(all_trades)}")
        
        # Calculate overall performance metrics
        analyzer = PerformanceAnalyzer(max_investment_per_trade=args.max_investment)
        overall_metrics = analyzer.calculate_performance_metrics(all_trades, initial_capital=args.initial_capital, years=args.years)
        
        # Generate yearly summary
        yearly_summary = analyzer.generate_yearly_summary(all_trades, initial_capital=args.initial_capital)
        
        # Save reports
        os.makedirs(args.output, exist_ok=True)
        
        # Save overall metrics
        with open(os.path.join(args.output, 'overall_metrics.yaml'), 'w') as f:
            yaml.dump(overall_metrics, f, default_flow_style=False)
            
        # Save yearly summary
        yearly_summary.to_csv(os.path.join(args.output, 'yearly_summary.csv'))
        
        # Calculate capital allocation for each trade
        # Sort trades chronologically
        sorted_trades = sorted(all_trades, key=lambda t: t.entry_date)
        cash_balance = args.initial_capital
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
        trade_log.to_csv(os.path.join(args.output, 'trade_log.csv'), index=False)
        
        logger.info(f"Analysis complete. Reports saved to {args.output}")
        
        # Print summary
        print("\nOverall Performance Summary:")
        print(f"Total Trades: {overall_metrics['total_trades']}")
        print(f"Win Rate: {overall_metrics['win_rate']:.2f}%")
        print(f"Initial Capital: ₹{overall_metrics['initial_capital']:,.2f}")
        print(f"Max Capital Used: ₹{overall_metrics['max_capital_used']:,.2f}")
        print(f"Additional Capital Required: ₹{overall_metrics['additional_capital_required']:,.2f}")
        print(f"Final Capital: ₹{overall_metrics['final_capital']:,.2f}")
        print(f"Realized P&L: ₹{overall_metrics['realized_pnl']:,.2f}")
        print(f"CAGR: {overall_metrics['cagr']:.2f}%")
        print(f"Sharpe Ratio: {overall_metrics['sharpe_ratio']:.2f}")
        print(f"Maximum Drawdown: {overall_metrics['max_drawdown']:.2f}%")
        print(f"Average Capital Utilization: {overall_metrics['avg_capital_utilization']:.2f}%")
        print(f"Maximum Concurrent Trades: {overall_metrics['max_concurrent_trades']}")
        
        # Print stock-specific performance if using stock configs
        if args.use_stock_configs and len(stock_configs) > 0:
            print("\nStock-Specific Performance:")
            # Group trades by symbol
            for symbol, trades in pd.DataFrame(sorted_trades).groupby('symbol'):
                if len(trades) > 0:
                    win_rate = len(trades[trades['pnl'] > 0]) / len(trades) * 100 if len(trades) > 0 else 0
                    total_pnl = sum(trades['pnl'].dropna())
                    print(f"{symbol}: {len(trades)} trades, Win Rate: {win_rate:.2f}%, P&L: ₹{total_pnl:,.2f}")
        
    except Exception as e:
        logger.error(f"Error in performance analysis: {str(e)}")
        raise

if __name__ == '__main__':
    main() 