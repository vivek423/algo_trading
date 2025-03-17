#!/usr/bin/env python3
import pandas as pd
import argparse
import os
import logging
import yaml
from datetime import datetime, timedelta
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def load_data(input_file):
    """Load data from CSV file."""
    try:
        df = pd.read_csv(input_file, parse_dates=['timestamp'])
        logger.info(f"Loaded data from {input_file} with shape {df.shape}")
        return df
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        raise

def split_by_date(df, split_date=None, test_months=6):
    """
    Split data into training and testing sets based on date.
    
    Args:
        df: DataFrame with timestamp column
        split_date: Date to split on (anything before is training, after is testing)
        test_months: Number of months for testing if split_date is not provided
        
    Returns:
        train_df, test_df, split_date
    """
    # Ensure we have a timestamp column
    if 'timestamp' not in df.columns:
        raise ValueError("DataFrame must have a 'timestamp' column")
    
    # Convert timestamp to datetime if it's not already
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Sort by timestamp
    df = df.sort_values('timestamp')
    
    # Determine split date if not provided
    if split_date is None:
        # Use the last N months for testing
        max_date = df['timestamp'].max()
        split_date = max_date - pd.DateOffset(months=test_months)
        logger.info(f"Auto-calculated split date: {split_date} (using last {test_months} months for testing)")
    else:
        split_date = pd.to_datetime(split_date)
        logger.info(f"Using provided split date: {split_date}")
    
    # Split the data
    train_df = df[df['timestamp'] < split_date]
    test_df = df[df['timestamp'] >= split_date]
    
    logger.info(f"Training data: {len(train_df)} rows from {train_df['timestamp'].min()} to {train_df['timestamp'].max()}")
    logger.info(f"Testing data: {len(test_df)} rows from {test_df['timestamp'].min()} to {test_df['timestamp'].max()}")
    
    return train_df, test_df, split_date

def save_split_metadata(output_dir, split_date, train_df, test_df):
    """Save metadata about the data split."""
    metadata = {
        'split_timestamp': split_date.strftime('%Y-%m-%d'),
        'split_performed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'training_period': {
            'start_date': train_df['timestamp'].min().strftime('%Y-%m-%d'),
            'end_date': train_df['timestamp'].max().strftime('%Y-%m-%d'),
            'num_records': len(train_df)
        },
        'testing_period': {
            'start_date': test_df['timestamp'].min().strftime('%Y-%m-%d'),
            'end_date': test_df['timestamp'].max().strftime('%Y-%m-%d'),
            'num_records': len(test_df)
        }
    }
    
    metadata_file = os.path.join(output_dir, 'split_metadata.yaml')
    with open(metadata_file, 'w') as f:
        yaml.dump(metadata, f, default_flow_style=False)
    
    logger.info(f"Saved split metadata to {metadata_file}")
    return metadata

def main():
    parser = argparse.ArgumentParser(description='Split data into training and testing periods for out-of-time validation')
    parser.add_argument('--input', required=True, help='Path to input CSV file')
    parser.add_argument('--output-dir', required=True, help='Directory to save split files')
    parser.add_argument('--split-date', help='Date to split on (YYYY-MM-DD). If not provided, uses last N months for testing')
    parser.add_argument('--test-months', type=int, default=6, help='Number of months for testing if split-date not provided')
    
    args = parser.parse_args()
    
    try:
        # Create output directory
        os.makedirs(args.output_dir, exist_ok=True)
        
        # Load data
        df = load_data(args.input)
        
        # Split data
        train_df, test_df, split_date = split_by_date(df, args.split_date, args.test_months)
        
        # Save split data
        train_output = os.path.join(args.output_dir, 'training_data.csv')
        test_output = os.path.join(args.output_dir, 'testing_data.csv')
        
        train_df.to_csv(train_output, index=False)
        test_df.to_csv(test_output, index=False)
        
        logger.info(f"Saved training data to {train_output}")
        logger.info(f"Saved testing data to {test_output}")
        
        # Save metadata
        metadata = save_split_metadata(args.output_dir, split_date, train_df, test_df)
        
        # Print summary
        print("\nData Split Summary:")
        print(f"Training period: {metadata['training_period']['start_date']} to {metadata['training_period']['end_date']} ({metadata['training_period']['num_records']} records)")
        print(f"Testing period: {metadata['testing_period']['start_date']} to {metadata['testing_period']['end_date']} ({metadata['testing_period']['num_records']} records)")
        print(f"Split date: {metadata['split_timestamp']}")
        
    except Exception as e:
        logger.error(f"Error splitting data: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 