# Algorithmic Trading System

A Python-based algorithmic trading system that fetches market data from Zerodha's Kite Connect API, performs technical analysis, optimizes parameters, and back-tests trading strategies.

## Project Structure

```
algo_trading/
├── config/
│   ├── trading_config.yaml        # Stock selection configuration
│   └── technical_indicators.yaml  # Technical analysis parameters
├── data/
│   ├── inputs/                    # Raw OHLC data
│   └── outputs/                   # Processed data with indicators
├── logs/                         # Application logs & performance reports
├── scripts/
│   ├── data_fetcher.py           # Fetches OHLC data from Kite Connect
│   ├── technical_analysis.py      # Technical analysis calculations
│   ├── performance_analyzer.py    # Back-testing and performance metrics
│   ├── grid_search.py            # Parameter optimization
│   ├── update_config.py          # Auto-updates config with best params
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
   - Bollinger Bands
   - RSI (Relative Strength Index)
   - Combined signal generation
   - Stop-loss and take-profit calculation
   - All indicators are configurable via YAML

3. **Performance Analysis**
   - Back-testing of trading strategies
   - Comprehensive performance metrics:
     - CAGR (Compound Annual Growth Rate)
     - Sharpe Ratio
     - Win Rate
     - Maximum Drawdown
     - Capital Utilization
     - Trade Duration Analysis
   - Trade logging and reporting
   - Yearly performance summaries

4. **Parameter Optimization**
   - Grid search for optimal technical indicator parameters
   - Configurable metrics for optimization (Sharpe, CAGR, Win Rate)
   - Automatic configuration updates with best parameters
   - Memory-efficient processing of large parameter spaces

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
   
   Edit `config/technical_indicators.yaml` to adjust parameters or use the auto-update script (see below).

2. **Process Single Stock**
   ```bash
   python scripts/technical_analysis.py \
     --input data/inputs/RELIANCE_60minute.csv \
     --output data/outputs/RELIANCE_indicators.csv
   ```

3. **Process All Stocks**
   ```bash
   python scripts/technical_analysis.py \
     --all \
     --output data/outputs/all_stocks_indicators.csv
   ```

### Performance Analysis

1. **Run Backtest**
   ```bash
   python scripts/performance_analyzer.py \
     --input data/outputs/all_stocks_indicators.csv \
     --output logs \
     --max-investment 5000 \
     --initial-capital 10000
   ```

2. **View Results**
   - Check the console output for summary metrics
   - Detailed reports are saved in the `logs/` directory:
     - `overall_metrics.yaml`: Full performance metrics
     - `yearly_summary.csv`: Year-by-year performance
     - `trade_log.csv`: Detailed record of all trades

### Parameter Optimization

1. **Run Grid Search**
   ```bash
   python scripts/grid_search.py \
     --input data/outputs/all_stocks_indicators.csv \
     --output logs \
     --max-investment 5000 \
     --initial-capital 10000 \
     --max-combinations 1000
   ```

2. **Auto-Update Configuration with Best Parameters**
   ```bash
   # Use best Sharpe Ratio (default)
   python scripts/update_config.py
   
   # Or optimize for CAGR
   python scripts/update_config.py --metric cagr
   
   # Or optimize for Win Rate
   python scripts/update_config.py --metric win_rate
   ```
   This automatically:
   - Updates the config file with the best parameters
   - Creates a backup of the previous configuration
   - Regenerates the indicators file with the new parameters

## Performance Metrics Explained

- **CAGR**: Compound Annual Growth Rate - the mean annual growth rate over the investment period
- **Sharpe Ratio**: Risk-adjusted return - higher is better, values above 1 are good
- **Win Rate**: Percentage of trades that were profitable
- **Maximum Drawdown**: Largest peak-to-trough decline in portfolio value
- **Capital Utilization**: Average percentage of capital deployed in trades
- **Maximum Concurrent Trades**: Highest number of open trades at one time

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
- bb_lower: Bollinger Bands lower band
- bb_middle: Bollinger Bands middle band
- bb_upper: Bollinger Bands upper band
- rsi: Relative Strength Index
- signal_combined: Combined signal (1 = buy, -1 = sell, 0 = hold)
- stop_loss: Calculated stop loss price
- take_profit: Calculated take profit price

## Error Handling

- Comprehensive logging in the `logs/` directory
- Data integrity verification
- Automatic retries for API calls
- Validation of input data and configurations
- Robust date handling for performance calculations

## Copyright Notice

© 2024 DataBull. All rights reserved.

This is proprietary software. Unauthorized copying, modification, distribution, or use of this software, via any medium, is strictly prohibited.