# Algorithmic Trading System

A Python-based algorithmic trading system that fetches market data from Zerodha's Kite Connect API and performs technical analysis.

## Project Structure

```
algo_trading/
├── config/
│   ├── trading_config.yaml        # Stock selection configuration
│   └── technical_indicators.yaml  # Technical analysis parameters
├── data/
│   ├── inputs/                    # Raw OHLC data
│   └── outputs/                   # Processed data with indicators
├── logs/                         # Application logs
├── scripts/
│   ├── data_fetcher.py           # Fetches OHLC data from Kite Connect
│   ├── technical_analysis.py      # Technical analysis calculations
│   └── get_request_token.py       # Kite Connect authentication
├── .env                          # API credentials (not tracked in git)
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Features

1. **Data Fetching**
   - Automated OHLC data fetching from Kite Connect API
   - Configurable stock selection (specific symbols or all equity stocks)
   - Incremental updates to avoid redundant downloads
   - Automated scheduling via cron jobs

2. **Technical Analysis**
   - MACD (Moving Average Convergence Divergence)
   - Support and Resistance levels
   - Average True Range (ATR)
   - Exponential Moving Average (EMA)
   - All indicators are configurable via YAML

## Setup

1. **Environment Setup**
   ```bash
   # Create virtual environment
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **API Configuration**
   Create a `.env` file with your Kite Connect credentials:
   ```
   KITE_API_KEY=your_api_key
   KITE_API_SECRET=your_api_secret
   ```

3. **Authentication**
   ```bash
   python scripts/get_request_token.py
   ```
   Follow the browser prompt to log in to your Zerodha account.

## Usage

### Data Fetching

1. **Configure Stock Selection**
   
   Edit `config/trading_config.yaml`:
   ```yaml
   # For specific stocks
   stocks:
     - RELIANCE
     - TCS
     - HDFCBANK
   
   # Or for all equity stocks
   stocks: all
   ```

2. **Run Data Fetcher**
   ```bash
   python scripts/data_fetcher.py
   ```

3. **Schedule Data Fetching**
   
   The system is configured to run during market hours (9:17 AM to 4:15 PM IST):
   ```bash
   crontab crontab_config.txt
   ```

### Technical Analysis

1. **Configure Indicators**
   
   Edit `config/technical_indicators.yaml` to adjust parameters:
   ```yaml
   macd:
     fast_period: 12
     slow_period: 26
     signal_period: 9
   
   support_resistance:
     support_period: 20
     resistance_period: 20
   ```

2. **Process Single Stock**
   ```bash
   python scripts/technical_analysis.py \
     --input data/inputs/RELIANCE_60minute.csv \
     --output data/outputs/RELIANCE_indicators.csv
   ```

## Data Structure

### Input Data (OHLC)
- timestamp: Datetime index
- open: Opening price
- high: High price
- low: Low price
- close: Closing price
- volume: Trading volume

### Generated Indicators
- macd_line: MACD line
- macd_signal: MACD signal line
- macd_hist: MACD histogram
- support_XX: Support level (XX = period)
- resistance_XX: Resistance level (XX = period)
- atr: Average True Range
- atr_threshold: ATR relative to price
- ema_XX: Exponential Moving Average (XX = period)

## Error Handling

- Comprehensive logging in the `logs/` directory
- Data integrity verification
- Automatic retries for API calls
- Validation of input data and configurations

## Copyright Notice

© 2024 DataBull. All rights reserved.

This is proprietary software. Unauthorized copying, modification, distribution, or use of this software, via any medium, is strictly prohibited.

## Disclaimer

This software is for educational purposes only. Use it at your own risk. The authors and contributors are not responsible for any financial losses incurred using this system. 