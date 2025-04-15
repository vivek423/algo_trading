import pandas as pd
import pandas_ta as ta
import yaml
import os
from typing import Optional, Dict, Union, List
import logging
import glob
import sys
from datetime import datetime

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
            # Defensive checks
            if df is None:
                logger.error("DataFrame is None in calculate_macd")
                raise ValueError("DataFrame cannot be None")
                
            if 'close' not in df.columns:
                logger.error(f"Missing 'close' column in DataFrame. Available columns: {df.columns.tolist()}")
                raise ValueError("Missing required column 'close' for MACD calculation")
                
            # Check for NaN values in close
            if df['close'].isna().any():
                logger.warning(f"DataFrame contains NaN values in 'close' column. Filling with forward fill method.")
                df['close'] = df['close'].ffill()
                
            # Get MACD parameters
            fast_period = self.config['macd']['fast_period']
            slow_period = self.config['macd']['slow_period']
            signal_period = self.config['macd']['signal_period']
            
            # Calculate MACD
            macd = ta.macd(
                close=df['close'],
                fast=fast_period,
                slow=slow_period,
                signal=signal_period
            )
            
            # Create column names
            macd_line_col = f'MACD_{fast_period}_{slow_period}_{signal_period}'
            macd_signal_col = f'MACDs_{fast_period}_{slow_period}_{signal_period}'
            macd_hist_col = f'MACDh_{fast_period}_{slow_period}_{signal_period}'
            
            # Check if MACD calculation returned expected columns
            if macd is None or macd_line_col not in macd.columns:
                logger.error("MACD calculation failed or returned unexpected structure")
                # Create default columns with NaN values to prevent further errors
                df['macd_line'] = float('nan')
                df['macd_signal'] = float('nan')
                df['macd_hist'] = float('nan')
                return df
            
            # Rename columns to match requirements
            df['macd_line'] = macd[macd_line_col]
            df['macd_signal'] = macd[macd_signal_col]
            df['macd_hist'] = macd[macd_hist_col]
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating MACD: {str(e)}")
            # Create default columns with NaN values to prevent further errors
            df['macd_line'] = float('nan')
            df['macd_signal'] = float('nan')
            df['macd_hist'] = float('nan')
            return df
            
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
                            ((df['macd_line'] < 0) & (df['macd_signal'] < 0)) & \
                            (((df['close'] - df[f'support_{support_period}']) / df['close']) <= df['atr_threshold'])
            
            short_condition = bearish_crossover & \
                            (df['close'] < df[f'ema_{ema_period}']) & \
                            (df['close'] < df[f'resistance_{resistance_period}']) & \
                            ((df['macd_line'] > 0) & (df['macd_signal'] > 0)) & \
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
            # Defensive check
            if df is None:
                logger.error("DataFrame is None in calculate_all_indicators")
                raise ValueError("DataFrame cannot be None")
                
            # Check for required columns
            required_columns = ['open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"Missing required columns: {missing_columns}")
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Make a copy to avoid modifying the original
            df = df.copy()
            
            # Handle potential timestamp issues
            if 'timestamp' in df.columns and not df.index.name == 'timestamp':
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            
            # Calculate each indicator wrapped in try-except to continue if one fails
            try:
                df = self.calculate_macd(df)
            except Exception as e:
                logger.error(f"Error calculating MACD: {str(e)}")
                df['macd_line'] = float('nan')
                df['macd_signal'] = float('nan')
                df['macd_hist'] = float('nan')
            
            try:
                df = self.calculate_support_resistance(df)
            except Exception as e:
                logger.error(f"Error calculating support/resistance: {str(e)}")
                df[f'support_{self.config["support_resistance"]["support_period"]}'] = float('nan')
                df[f'resistance_{self.config["support_resistance"]["resistance_period"]}'] = float('nan')
            
            try:
                df = self.calculate_atr(df)
            except Exception as e:
                logger.error(f"Error calculating ATR: {str(e)}")
                df['atr'] = float('nan')
                df['atr_threshold'] = float('nan')
            
            try:
                df = self.calculate_ema(df)
            except Exception as e:
                logger.error(f"Error calculating EMA: {str(e)}")
                df[f'ema_{self.config["ema"]["period"]}'] = float('nan')
            
            try:
                df = self.calculate_bollinger_bands(df)
            except Exception as e:
                logger.error(f"Error calculating Bollinger Bands: {str(e)}")
                df['bb_lower'] = float('nan')
                df['bb_middle'] = float('nan')
                df['bb_upper'] = float('nan')
            
            try:
                df = self.calculate_rsi(df)
            except Exception as e:
                logger.error(f"Error calculating RSI: {str(e)}")
                df['rsi'] = float('nan')
            
            try:
                df = self.generate_signals(df)
            except Exception as e:
                logger.error(f"Error generating signals: {str(e)}")
                df['signal_macd'] = 0
                df['signal_ema'] = 0
                df['signal_bollinger'] = 0
                df['signal_rsi'] = 0
                df['signal_combined'] = 0
            
            try:
                df = self.calculate_stop_loss_take_profit(df)
            except Exception as e:
                logger.error(f"Error calculating stop loss/take profit: {str(e)}")
                df['stop_loss'] = float('nan')
                df['take_profit'] = float('nan')
                df['risk_reward_ratio'] = float('nan')
            
            # Drop rows with too many NaN values, but don't be too strict
            # Keep rows with at least 70% of the indicator columns populated
            indicator_columns = [
                'macd_line', 'macd_signal', 'macd_hist',
                f'support_{self.config["support_resistance"]["support_period"]}', 
                f'resistance_{self.config["support_resistance"]["resistance_period"]}',
                'atr', 'atr_threshold',
                f'ema_{self.config["ema"]["period"]}',
                'bb_lower', 'bb_middle', 'bb_upper',
                'rsi'
            ]
            
            df_filtered = df.dropna(subset=indicator_columns, thresh=int(0.7 * len(indicator_columns)))
            
            if len(df_filtered) < len(df):
                logger.warning(f"Dropped {len(df) - len(df_filtered)} rows with too many NaN values")
            
            if len(df_filtered) == 0:
                logger.warning("All rows were dropped due to NaN values. Returning original dataframe with indicators.")
                return df
                
            return df_filtered
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {str(e)}")
            return df

def main():
    """Main function to run technical analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Calculate technical indicators for stock data.')
    parser.add_argument('--input', '-i', help='Path to input CSV file with OHLC data')
    parser.add_argument('--config', '-c', help='Path to technical indicators configuration file')
    parser.add_argument('--all', '-a', action='store_true', help='Process all stocks from trading config')
    parser.add_argument('--trading-config', '-t', default='config/trading_config.yaml', 
                        help='Path to trading configuration file (used with --all)')
    parser.add_argument('--input-dir', '-d', default='data/inputs/', 
                        help='Directory containing input CSV files (used with --all)')
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = 'data/outputs/indicators'
    os.makedirs(output_dir, exist_ok=True)
    
    # Validate arguments
    if args.all:
        if args.input:
            parser.error("When using --all, don't specify --input")
    else:
        if not args.input:
            parser.error("--input is required when not using --all")
    
    try:
        if args.all:
            # Define hardcoded output path for --all option
            output_file = os.path.join(output_dir, f"all_indicators_{datetime.now().strftime('%Y%m%d')}.csv")
            
            # Process all stocks from trading config
            trading_config_path = args.trading_config
            with open(trading_config_path, 'r') as f:
                trading_config = yaml.safe_load(f)
            
            # Support both old and new format for stocks configuration
            if isinstance(trading_config['stocks'], list):
                if trading_config['stocks'] and isinstance(trading_config['stocks'][0], dict):
                    # New format - list of dicts with symbol and config
                    stocks_config = trading_config['stocks']
                else:
                    # Old format - just a list of symbols
                    stocks_config = [{'symbol': symbol, 'config': None} for symbol in trading_config['stocks']]
            else:
                logger.error("Invalid stocks configuration format in trading_config.yaml")
                return
            
            interval = trading_config.get('interval', '60minute')
            all_results = []
            
            for stock_entry in stocks_config:
                symbol = stock_entry['symbol']
                config_path = stock_entry.get('config')
                
                input_file = os.path.join(args.input_dir, f"{symbol}_{interval}.csv")
                if not os.path.exists(input_file):
                    logger.warning(f"Input file for {symbol} not found: {input_file}")
                    continue
                
                logger.info(f"Processing {symbol}...")
                
                try:
                    # Initialize technical analysis with stock-specific config if available
                    # The TechnicalAnalysis class will handle missing files by falling back to default
                    ta = TechnicalAnalysis(config_path=config_path)
                    
                    df = ta.load_data(input_file)
                    df_with_indicators = ta.calculate_all_indicators(df)
                    
                    # Add stock symbol column
                    df_with_indicators['symbol'] = symbol
                    
                    all_results.append(df_with_indicators)
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {str(e)}")
                    # Continue with next stock instead of crashing
                    continue
            
            if all_results:
                # Combine all results
                combined_df = pd.concat(all_results)
                combined_df.to_csv(output_file)
                logger.info(f"Combined technical indicators for {len(all_results)} stocks saved to {output_file}")
            else:
                logger.error("No stock data was processed. Check input directory and stock symbols.")
        else:
            # Process single stock
            # Initialize technical analysis
            ta = TechnicalAnalysis(config_path=args.config)
            
            df = ta.load_data(args.input)
            df_with_indicators = ta.calculate_all_indicators(df)
            
            # Extract stock symbol from filename
            stock_symbol = os.path.basename(args.input).split('_')[0]
            df_with_indicators['symbol'] = stock_symbol
            
            # Define hardcoded output path for single stock
            output_file = os.path.join(output_dir, f"{stock_symbol}_indicators.csv")
            
            df_with_indicators.to_csv(output_file)
            logger.info(f"Technical indicators saved to {output_file}")
        
    except Exception as e:
        logger.error(f"Error processing technical indicators: {str(e)}")
        raise

if __name__ == '__main__':
    main() 