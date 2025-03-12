#!/usr/bin/env python3
import os
from datetime import datetime, timedelta
import pytz
import pandas as pd

def check_cron_status():
    # Path configurations
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data', 'inputs')
    log_file = os.path.join(base_dir, 'logs', 'data_fetcher.log')
    
    # Get current time in IST
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    print(f"\nCron Job Status Check - {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("-" * 50)
    
    # Check if it's a weekday
    if now.weekday() >= 5:
        print("Today is a weekend - cron job is not scheduled to run")
        return
    
    # Check if we're within market hours (9:17 AM to 4:15 PM IST)
    market_start = now.replace(hour=9, minute=17, second=0, microsecond=0)
    market_end = now.replace(hour=16, minute=15, second=0, microsecond=0)
    
    if not (market_start <= now <= market_end):
        print("Current time is outside market hours - cron job is not scheduled to run")
        return
    
    # Check log file
    if os.path.exists(log_file):
        last_modified = datetime.fromtimestamp(os.path.getmtime(log_file)).astimezone(ist)
        print(f"\nLog File Status:")
        print(f"Last modified: {last_modified.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # Check last few lines of log
        with open(log_file, 'r') as f:
            last_lines = f.readlines()[-5:]
            print("\nLast few log entries:")
            for line in last_lines:
                print(line.strip())
    else:
        print("\nLog file not found!")
    
    # Check CSV files
    print("\nData File Status:")
    csv_files = [f for f in os.listdir(data_dir) if f.endswith('_60minute.csv')]
    
    if csv_files:
        for csv_file in sorted(csv_files)[:5]:  # Show first 5 files
            file_path = os.path.join(data_dir, csv_file)
            last_modified = datetime.fromtimestamp(os.path.getmtime(file_path)).astimezone(ist)
            
            # Check last timestamp in the file
            try:
                df = pd.read_csv(file_path)
                if not df.empty and 'timestamp' in df.columns:
                    last_data = pd.to_datetime(df['timestamp']).max()
                    print(f"\n{csv_file}:")
                    print(f"Last modified: {last_modified.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                    print(f"Latest data timestamp: {last_data}")
            except Exception as e:
                print(f"\nError reading {csv_file}: {str(e)}")
        
        if len(csv_files) > 5:
            print(f"\n... and {len(csv_files) - 5} more files")
    else:
        print("No CSV files found in data directory!")

if __name__ == "__main__":
    check_cron_status() 