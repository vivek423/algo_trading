import pandas as pd
import pandas_ta as ta
import yaml
import os
from typing import Optional, Dict, Union, List
import logging
import glob
import sys
import argparse

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'technical_analysis.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger(__name__)

class TechnicalAnalysis:
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize TechnicalAnalysis with configuration.
        
        Args:
            config_path: Path to YAML configuration file. If None, uses default path.
        """
        # Default config path as fallback
        self.default_config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'config', 
            'technical_indicators.yaml'
        )
        
        if config_path is None:
            config_path = self.default_config_path
        
        try:
            self.config = self._load_config(config_path)
        except Exception as e:
            # If loading the specified config fails, try the default
            if config_path != self.default_config_path:
                logger.warning(f"Failed to load config from {config_path}: {str(e)}. Falling back to default config.")
                self.config = self._load_config(self.default_config_path)
            else:
                # If default config also fails, re-raise the exception
                raise
                
        self.validate_config()
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded technical analysis configuration from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            raise
            
    def validate_config(self):
        """Validate the configuration parameters."""
        required_sections = ['macd', 'support_resistance', 'atr', 'ema', 'columns']
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required section '{section}' in configuration")
                
    def load_data(self, file_path: str) -> pd.DataFrame:
        """
        Load OHLC data from CSV file.
        
        Args:
            file_path: Path to CSV file containing OHLC data
            
        Returns:
            pd.DataFrame: DataFrame with OHLC data
        """
        try:
            df = pd.read_csv(file_path)
            
            # Ensure required columns exist
            required_columns = ['timestamp', 'open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Set timestamp as index
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading data from {file_path}: {str(e)}")
            raise
            
    def calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate MACD indicator."""
        try:
            macd = ta.macd(
                close=df['close'],
                fast=self.config['macd']['fast_period'],
                slow=self.config['macd']['slow_period'],
                signal=self.config['macd']['signal_period']
            )
            
            # Rename columns to match requirements
            df['macd_line'] = macd[f'MACD_{self.config["macd"]["fast_period"]}_{self.config["macd"]["slow_period"]}_{self.config["macd"]["signal_period"]}']
            df['macd_signal'] = macd[f'MACDs_{self.config["macd"]["fast_period"]}_{self.config["macd"]["slow_period"]}_{self.config["macd"]["signal_period"]}']
            df['macd_hist'] = macd[f'MACDh_{self.config["macd"]["fast_period"]}_{self.config["macd"]["slow_period"]}_{self.config["macd"]["signal_period"]}']
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating MACD: {str(e)}")
            raise
            
    def calculate_support_resistance(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate support and resistance levels."""
        try:
            support_period = self.config['support_resistance']['support_period']
            resistance_period = self.config['support_resistance']['resistance_period']
            
            df[f'support_{support_period}'] = df['low'].rolling(window=support_period).min()
            df[f'resistance_{resistance_period}'] = df['high'].rolling(window=resistance_period).max()
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating support/resistance: {str(e)}")
            raise
            
    def calculate_atr(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate ATR and ATR threshold."""
        try:
            atr_window = self.config['atr']['window']
            
            df['atr'] = ta.atr(
                high=df['high'],
                low=df['low'],
                close=df['close'],
                length=atr_window
            )
            df['atr_threshold'] = df['atr'] / df['close']
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating ATR: {str(e)}")
            raise
            
    def calculate_ema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate EMA."""
        try:
            ema_period = self.config['ema']['period']
            
            df[f'ema_{ema_period}'] = ta.ema(
                close=df['close'],
                length=ema_period
            )
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating EMA: {str(e)}")
            raise
            
    def calculate_bollinger_bands(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Bollinger Bands."""
        try:
            bb_length = self.config.get('bollinger_bands', {}).get('length', 30)
            bb_std = self.config.get('bollinger_bands', {}).get('std', 2.0)
            
            bb = ta.bbands(df['close'], length=bb_length, std=bb_std)
            df['bb_lower'] = bb[f'BBL_{bb_length}_{bb_std}']
            df['bb_middle'] = bb[f'BBM_{bb_length}_{bb_std}']
            df['bb_upper'] = bb[f'BBU_{bb_length}_{bb_std}']
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {str(e)}")
            raise
    
    def calculate_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate RSI."""
        try:
            rsi_length = self.config.get('rsi', {}).get('length', 13)
            
            df['rsi'] = ta.rsi(df['close'], length=rsi_length)
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {str(e)}")
            raise
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals based on technical indicators."""
        try:
            # Get configuration parameters
            ema_period = self.config['ema']['period']
            support_period = self.config['support_resistance']['support_period']
            resistance_period = self.config['support_resistance']['resistance_period']
            
            rsi_oversold = self.config.get('rsi', {}).get('oversold', 30)
            rsi_overbought = self.config.get('rsi', {}).get('overbought', 70)

            # --- MACD-based signal ---
            bullish_crossover = (df['macd_line'] > df['macd_signal']) & (df['macd_line'].shift(1) <= df['macd_signal'].shift(1))
            bearish_crossover = (df['macd_line'] < df['macd_signal']) & (df['macd_line'].shift(1) >= df['macd_signal'].shift(1))
            
            long_condition = bullish_crossover & \
                            (df['close'] > df[f'ema_{ema_period}']) & \
                            (df['close'] > df[f'support_{support_period}']) & \
                            (df['macd_line'] < 0) & (df['macd_signal'] < 0) & \
                            (((df['close'] - df[f'support_{support_period}']) / df['close']) <= df['atr_threshold'])
            
            short_condition = bearish_crossover & \
                            (df['close'] < df[f'ema_{ema_period}']) & \
                            (df['close'] < df[f'resistance_{resistance_period}']) & \
                            (df['macd_line'] > 0) & (df['macd_signal'] > 0) & \
                            (((df[f'resistance_{resistance_period}'] - df['close']) / df['close']) <= df['atr_threshold'])
            
            df['macd_atr_signal'] = 0
            df.loc[long_condition, 'macd_atr_signal'] = 1
            df.loc[short_condition, 'macd_atr_signal'] = -1
            
            # --- Bollinger Bands & RSI-based signal ---
            bollinger_long = (df['close'] < df['bb_lower']) & (df['rsi'] < rsi_oversold)
            bollinger_short = (df['close'] > df['bb_upper']) & (df['rsi'] > rsi_overbought)
            
            df['bollinger_atr_signal'] = 0
            df.loc[bollinger_long, 'bollinger_atr_signal'] = 1
            df.loc[bollinger_short, 'bollinger_atr_signal'] = -1
            
            # --- Combine signals ---
            def final_signal(row):
                # Compute indicator-based signal
                macd_sig = row['macd_atr_signal']
                boll_sig = row['bollinger_atr_signal']
                total = macd_sig + boll_sig
                
                if total < 0:
                    return -1  # Sell
                elif total == 0:
                    # If both individual signals are zero, then hold; otherwise, treat as buy
                    if row['macd_atr_signal'] == 0 and row['bollinger_atr_signal'] == 0:
                        return 0  # Hold
                    else:
                        return 1  # Buy
                else:
                    return 1  # Buy
            
            df['signal_combined'] = df.apply(final_signal, axis=1)
            
            return df
            
        except Exception as e:
            logger.error(f"Error generating signals: {str(e)}")
            raise
    
    def calculate_stop_loss_take_profit(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate stop loss and take profit levels based on ATR for buy signals only."""
        try:
            # Get ATR multipliers from config or use defaults
            sl_atr_multiplier = self.config.get('risk_management', {}).get('stop_loss_atr_multiplier', 2.0)
            tp_atr_multiplier = self.config.get('risk_management', {}).get('take_profit_atr_multiplier', 3.0)
            
            # Initialize columns with NaN
            df['stop_loss'] = float('nan')
            df['take_profit'] = float('nan')
            
            # Calculate stop loss and take profit only for buy signals
            buy_signals = df['signal_combined'] == 1
            
            # For buy signals: stop loss is entry price - ATR*multiplier, take profit is entry price + ATR*multiplier
            if buy_signals.any():
                df.loc[buy_signals, 'stop_loss'] = df.loc[buy_signals, 'close'] - (df.loc[buy_signals, 'atr'] * sl_atr_multiplier)
                df.loc[buy_signals, 'take_profit'] = df.loc[buy_signals, 'close'] + (df.loc[buy_signals, 'atr'] * tp_atr_multiplier)
                
                # Calculate risk-reward ratio for buy signals
                df.loc[buy_signals, 'risk_reward_ratio'] = (df.loc[buy_signals, 'take_profit'] - df.loc[buy_signals, 'close']) / (df.loc[buy_signals, 'close'] - df.loc[buy_signals, 'stop_loss'])
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating stop loss and take profit: {str(e)}")
            raise
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators."""
        try:
            df = self.calculate_macd(df)
            df = self.calculate_support_resistance(df)
            df = self.calculate_atr(df)
            df = self.calculate_ema(df)
            df = self.calculate_bollinger_bands(df)
            df = self.calculate_rsi(df)
            df = self.generate_signals(df)
            df = self.calculate_stop_loss_take_profit(df)
            
            # Drop NaN values from calculations
            df.dropna(subset=[
                f'ema_{self.config["ema"]["period"]}', 
                'macd_line', 'macd_signal', 'macd_hist',
                f'support_{self.config["support_resistance"]["support_period"]}', 
                f'resistance_{self.config["support_resistance"]["resistance_period"]}',
                'atr', 'atr_threshold',
                'bb_lower', 'bb_middle', 'bb_upper',
                'rsi'
            ], inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {str(e)}")
            raise

def main():
    """Main function to run technical analysis."""
    parser = argparse.ArgumentParser(description='Generate technical indicators for stock data')
    parser.add_argument('--input', required=True, help='Input data file path (CSV)')
    parser.add_argument('--output', required=True, help='Output data file path (CSV)')
    parser.add_argument('--config', help='Technical indicators configuration file path')
    parser.add_argument('--all', action='store_true', help='Process all stocks from trading config')
    parser.add_argument('--trading-config', default='config/trading_config.yaml', help='Trading configuration file path')
    parser.add_argument('--input-dir', help='Input directory containing data files')
    parser.add_argument('--start-date', help='Start date for data filtering (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for data filtering (YYYY-MM-DD)')
    parser.add_argument('--train-test-split', action='store_true', help='Split data into training and testing sets')
    parser.add_argument('--test-months', type=int, default=6, help='Number of months to set aside for testing')
    parser.add_argument('--output-test', help='Output file path for test data')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.all and args.config:
        logger.error("Cannot use --all and --config together")
        sys.exit(1)
    
    if args.all and not os.path.exists(args.trading_config):
        logger.error(f"Trading config file not found: {args.trading_config}")
        sys.exit(1)
        
    if args.train_test_split and not args.output_test:
        logger.error("--output-test must be specified when using --train-test-split")
        sys.exit(1)
    
    # Process all stocks from trading config
    if args.all:
        # Load trading configuration
        with open(args.trading_config, 'r') as file:
            trading_config = yaml.safe_load(file)
        
        if 'stocks' not in trading_config:
            logger.error("No stocks found in trading config")
            sys.exit(1)
            
        # Load input data
        if args.input_dir:
            input_file = os.path.join(args.input_dir, args.input)
        else:
            input_file = args.input
            
        logger.info(f"Loading data from {input_file}")
        df = pd.read_csv(input_file, parse_dates=['timestamp'])
        
        # Filter by date range if specified
        if args.start_date or args.end_date:
            original_size = len(df)
            
            if args.start_date:
                start_date = pd.to_datetime(args.start_date)
                df = df[df['timestamp'] >= start_date]
                logger.info(f"Filtered data to start from {args.start_date}")
                
            if args.end_date:
                end_date = pd.to_datetime(args.end_date)
                df = df[df['timestamp'] <= end_date]
                logger.info(f"Filtered data to end at {args.end_date}")
                
            logger.info(f"Date filtering: {original_size} -> {len(df)} rows")
        
        # Handle train-test split if requested
        if args.train_test_split:
            # Sort by timestamp to ensure chronological split
            df.sort_values('timestamp', inplace=True)
            
            # Find the cutoff date for splitting
            latest_date = df['timestamp'].max()
            cutoff_date = latest_date - pd.DateOffset(months=args.test_months)
            
            # Split the data
            train_data = df[df['timestamp'] <= cutoff_date].copy()
            test_data = df[df['timestamp'] > cutoff_date].copy()
            
            logger.info(f"Train-test split: {len(train_data)} training rows, {len(test_data)} testing rows")
            logger.info(f"Training period: {train_data['timestamp'].min()} to {train_data['timestamp'].max()}")
            logger.info(f"Testing period: {test_data['timestamp'].min()} to {test_data['timestamp'].max()}")
            
            # Continue with training data for now
            df = train_data
        else:
            test_data = None
        
        # Process each stock
        results = []
        for stock in trading_config['stocks']:
            # Support both old and new format for stock configurations
            if isinstance(stock, dict):
                symbol = stock.get('symbol')
                config_path = stock.get('config')
            else:
                symbol = stock
                config_path = None
                
            if not symbol:
                logger.warning(f"Skipping stock with no symbol: {stock}")
                continue
                
            # Filter data for this stock
            stock_data = df[df['symbol'] == symbol].copy()
            
            if len(stock_data) < 10:
                logger.warning(f"Insufficient data for {symbol} (only {len(stock_data)} rows). Skipping.")
                continue
                
            logger.info(f"Processing {symbol} with {len(stock_data)} data points")
            
            # Determine the configuration to use
            if config_path:
                # If specific config is provided for this stock
                config_path = os.path.join(os.path.dirname(args.trading_config), config_path)
                if not os.path.exists(config_path):
                    logger.warning(f"Configuration file not found for {symbol}: {config_path}")
                    config_path = None
            
            # If no valid config found, use default
            if not config_path and args.config:
                config_path = args.config
                
            # Process the stock data
            ta = TechnicalAnalysis(config_path=config_path)
            stock_data = ta.calculate_all_indicators(stock_data)
            
            results.append(stock_data)
            
        # Combine results and save
        if results:
            combined_results = pd.concat(results, ignore_index=True)
            combined_results.to_csv(args.output, index=False)
            logger.info(f"Saved {len(combined_results)} rows to {args.output}")
            
            # Save test data if split was requested
            if args.train_test_split and test_data is not None:
                # Process test data with the same configurations
                test_results = []
                for stock in trading_config['stocks']:
                    if isinstance(stock, dict):
                        symbol = stock.get('symbol')
                        config_path = stock.get('config')
                    else:
                        symbol = stock
                        config_path = None
                        
                    if not symbol:
                        continue
                        
                    # Filter test data for this stock
                    stock_test_data = test_data[test_data['symbol'] == symbol].copy()
                    
                    if len(stock_test_data) < 10:
                        logger.warning(f"Insufficient test data for {symbol} (only {len(stock_test_data)} rows). Skipping.")
                        continue
                        
                    logger.info(f"Processing test data for {symbol} with {len(stock_test_data)} data points")
                    
                    # Use the same configuration as for training
                    if config_path:
                        config_path = os.path.join(os.path.dirname(args.trading_config), config_path)
                        if not os.path.exists(config_path):
                            config_path = None
                            
                    if not config_path and args.config:
                        config_path = args.config
                        
                    ta = TechnicalAnalysis(config_path=config_path)
                    stock_test_data = ta.calculate_all_indicators(stock_test_data)
                    
                    test_results.append(stock_test_data)
                    
                if test_results:
                    combined_test_results = pd.concat(test_results, ignore_index=True)
                    combined_test_results.to_csv(args.output_test, index=False)
                    logger.info(f"Saved {len(combined_test_results)} test rows to {args.output_test}")
        else:
            logger.warning("No data processed. Output file not created.")
    
    # Process single stock with specified config
    else:
        # Load input data
        if args.input_dir:
            input_file = os.path.join(args.input_dir, args.input)
        else:
            input_file = args.input
            
        logger.info(f"Loading data from {input_file}")
        df = pd.read_csv(input_file, parse_dates=['timestamp'])
        
        # Filter by date range if specified
        if args.start_date or args.end_date:
            original_size = len(df)
            
            if args.start_date:
                start_date = pd.to_datetime(args.start_date)
                df = df[df['timestamp'] >= start_date]
                logger.info(f"Filtered data to start from {args.start_date}")
                
            if args.end_date:
                end_date = pd.to_datetime(args.end_date)
                df = df[df['timestamp'] <= end_date]
                logger.info(f"Filtered data to end at {args.end_date}")
                
            logger.info(f"Date filtering: {original_size} -> {len(df)} rows")
        
        # Handle train-test split if requested
        if args.train_test_split:
            # Sort by timestamp to ensure chronological split
            df.sort_values('timestamp', inplace=True)
            
            # Find the cutoff date for splitting
            latest_date = df['timestamp'].max()
            cutoff_date = latest_date - pd.DateOffset(months=args.test_months)
            
            # Split the data
            train_data = df[df['timestamp'] <= cutoff_date].copy()
            test_data = df[df['timestamp'] > cutoff_date].copy()
            
            logger.info(f"Train-test split: {len(train_data)} training rows, {len(test_data)} testing rows")
            logger.info(f"Training period: {train_data['timestamp'].min()} to {train_data['timestamp'].max()}")
            logger.info(f"Testing period: {test_data['timestamp'].min()} to {test_data['timestamp'].max()}")
            
            # Continue with training data for now
            df = train_data
        else:
            test_data = None
        
        # Calculate technical indicators
        ta = TechnicalAnalysis(config_path=args.config)
        result = ta.calculate_all_indicators(df)
        
        # Save results
        result.to_csv(args.output, index=False)
        logger.info(f"Saved {len(result)} rows to {args.output}")
        
        # Save test data if split was requested
        if args.train_test_split and test_data is not None:
            test_result = ta.calculate_all_indicators(test_data)
            test_result.to_csv(args.output_test, index=False)
            logger.info(f"Saved {len(test_result)} test rows to {args.output_test}")

if __name__ == '__main__':
    main() 