import pandas as pd
import pandas_ta as ta
import yaml
import os
from typing import Optional, Dict, Union
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TechnicalAnalysis:
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize TechnicalAnalysis with configuration.
        
        Args:
            config_path: Path to YAML configuration file. If None, uses default path.
        """
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'config', 
                'technical_indicators.yaml'
            )
        
        self.config = self._load_config(config_path)
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
            
    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators."""
        try:
            df = self.calculate_macd(df)
            df = self.calculate_support_resistance(df)
            df = self.calculate_atr(df)
            df = self.calculate_ema(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {str(e)}")
            raise
            
def main():
    """Example usage of TechnicalAnalysis class."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Calculate technical indicators for OHLC data')
    parser.add_argument('--input', type=str, required=True, help='Input CSV file path')
    parser.add_argument('--output', type=str, required=True, help='Output CSV file path')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    args = parser.parse_args()
    
    # Initialize technical analysis
    ta_analyzer = TechnicalAnalysis(config_path=args.config)
    
    # Load and process data
    df = ta_analyzer.load_data(args.input)
    df = ta_analyzer.calculate_all_indicators(df)
    
    # Save results
    df.to_csv(args.output)
    logger.info(f"Saved technical indicators to {args.output}")

if __name__ == "__main__":
    main() 