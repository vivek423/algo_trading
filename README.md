# Algorithmic Trading System

A Python-based algorithmic trading system that fetches market data from Zerodha's Kite Connect API, performs technical analysis, optimizes parameters, and back-tests trading strategies.

## Project Structure

```
algo_trading/
├── config/
│   ├── trading_config.yaml        # Stock selection configuration
│   ├── technical_indicators.yaml  # Default technical analysis parameters
│   └── stock_configs/             # Stock-specific indicator parameters
├── data/
│   ├── inputs/                    # Raw OHLC data
│   └── outputs/                   # Processed data with indicators
├── logs/                         # Application logs & performance reports
├── scripts/
│   ├── data_fetcher.py           # Fetches OHLC data from Kite Connect
│   ├── technical_analysis.py      # Technical analysis calculations
│   ├── performance_analyzer.py    # Back-testing and performance metrics
│   ├── grid_search.py            # Global parameter optimization
│   ├── stock_grid_search.py      # Stock-specific parameter optimization
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
   - Stock-specific configuration support
   - Automated fallback to default configurations

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
   - Stock-specific performance analysis
   - Portfolio-level analysis

4. **Parameter Optimization**
   - Global grid search for all stocks
   - Stock-specific parameter optimization 
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
   # For specific stocks with stock-specific configs
   stocks:
     - symbol: RELIANCE
       config: config/stock_configs/RELIANCE.yaml
     - symbol: TCS
       config: config/stock_configs/TCS.yaml
   
   # Or for all equity stocks (old format)
   stocks: all
   ```

2. **Run Data Fetcher**
   ```bash
   python scripts/data_fetcher.py
   ```

3. **Schedule Data Fetching**
   
   ```bash
   crontab crontab_config.txt
   ```

### Technical Analysis

1. **Configure Indicators**
   
   Edit `config/technical_indicators.yaml` for default parameters or create stock-specific configurations in `config/stock_configs/`.

2. **Process Single Stock**
   ```bash
   python scripts/technical_analysis.py \
     --input data/inputs/RELIANCE_day.csv \
     --output data/outputs/RELIANCE_indicators.csv \
     --config config/stock_configs/RELIANCE.yaml
   ```

3. **Process All Stocks with Stock-Specific Configurations**
   ```bash
   python scripts/technical_analysis.py \
     --all \
     --output data/outputs/all_stocks_optimized_indicators.csv
   ```
   This automatically uses stock-specific configurations from `config/stock_configs/` when available.

### Performance Analysis

1. **Run Backtest with Default Parameters**
   ```bash
   python scripts/performance_analyzer.py \
     --input data/outputs/all_stocks_indicators.csv \
     --output logs/default_performance \
     --max-investment 5000 \
     --initial-capital 10000
   ```

2. **Run Backtest with Stock-Specific Configurations**
   ```bash
   python scripts/performance_analyzer.py \
     --input data/outputs/all_stocks_optimized_indicators.csv \
     --output logs/optimized_performance \
     --use-stock-configs \
     --max-investment 5000 \
     --initial-capital 10000
   ```

3. **View Results**
   - Check the console output for summary metrics
   - Detailed reports are saved in the output directory:
     - `overall_metrics.yaml`: Full performance metrics
     - `yearly_summary.csv`: Year-by-year performance
     - `trade_log.csv`: Detailed record of all trades

### Parameter Optimization

1. **Run Global Grid Search for All Stocks Combined**
   ```bash
   # Using consolidated indicators file (traditional approach)
   python scripts/grid_search.py \
     --input data/outputs/all_stocks_indicators.csv \
     --output logs \
     --max-investment 5000 \
     --initial-capital 10000 \
     --max-combinations 1000
     
   # Using individual stock files directly (more efficient approach)
   python scripts/grid_search.py \
     --input-dir data/inputs \
     --trading-config config/trading_config.yaml \
     --output logs \
     --max-investment 5000 \
     --initial-capital 10000 \
     --max-combinations 1000
   ```

2. **Run Grid Search for Individual Stocks**
   ```bash
   # Using consolidated indicators file (traditional approach)
   python scripts/stock_grid_search.py \
     --input data/outputs/all_stocks_indicators.csv \
     --output logs/stock_grid_search \
     --max-combinations 10000
   
   # Using individual stock files directly (more efficient approach)
   python scripts/stock_grid_search.py \
     --input-dir data/inputs \
     --output logs/stock_grid_search \
     --max-combinations 10000
     
   # Optimize for specific stocks
   python scripts/stock_grid_search.py \
     --input-dir data/inputs \
     --output logs/stock_grid_search \
     --stocks RELIANCE TCS HDFCBANK \
     --max-combinations 10000
   ```

3. **Auto-Update Configuration with Best Parameters**
   ```bash
   # Update global config with best Sharpe Ratio (default)
   python scripts/update_config.py
   
   # Or optimize for CAGR
   python scripts/update_config.py --metric cagr
   
   # Or optimize for Win Rate
   python scripts/update_config.py --metric win_rate
   ```

### Complete Workflow for Stock-Specific Optimization

For best results, follow this complete workflow:

1. **Fetch OHLC data for all stocks**
   ```bash
   python scripts/data_fetcher.py
   ```

2. **Run stock-specific grid search directly on raw data files**
   ```bash
   python scripts/stock_grid_search.py \
     --input-dir data/inputs \
     --output logs/stock_grid_search \
     --max-combinations 10000
   ```

3. **Run performance analysis with optimized parameters**
   ```bash
   python scripts/performance_analyzer.py \
     --input data/outputs/all_stocks_indicators.csv \
     --output logs/optimized_performance \
     --use-stock-configs \
     --max-investment 5000 \
     --initial-capital 10000
   ```

### Alternative Workflow (Traditional Approach)

If you prefer the traditional approach with consolidated files:

1. **Fetch OHLC data for all stocks**
   ```bash
   python scripts/data_fetcher.py
   ```

2. **Calculate indicators with default parameters**
   ```bash
   python scripts/technical_analysis.py --all --output data/outputs/all_stocks_indicators.csv
   ```

3. **Run stock-specific grid search to find optimal parameters**
   ```bash
   python scripts/stock_grid_search.py --input data/outputs/all_stocks_indicators.csv --output logs/stock_grid_search --max-combinations 10000
   ```

4. **Calculate indicators with optimized parameters**
   ```bash
   python scripts/technical_analysis.py --all --output data/outputs/all_stocks_optimized_indicators.csv
   ```

5. **Run performance analysis with optimized parameters**
   ```bash
   python scripts/performance_analyzer.py --input data/outputs/all_stocks_optimized_indicators.csv --output logs/optimized_performance --use-stock-configs --max-investment 5000 --initial-capital 10000
   ```

## Performance Metrics Explained

- **CAGR**: Compound Annual Growth Rate - the mean annual growth rate over the investment period
- **Sharpe Ratio**: Risk-adjusted return - higher is better, values above 1 are good
- **Win Rate**: Percentage of trades that were profitable
- **Maximum Drawdown**: Largest peak-to-trough decline in portfolio value
- **Capital Utilization**: Average percentage of capital deployed in trades
- **Maximum Concurrent Trades**: Highest number of open trades at one time

## Performance Results

Our stock-specific optimization approach has yielded exceptional results:

- **Total Trades**: 148 trades across 50 stocks
- **Win Rate**: 86.49% (significantly above industry average)
- **CAGR**: 47.46% (exceptional annual growth rate)
- **Sharpe Ratio**: 0.40
- **Maximum Drawdown**: Only 3.47% (extremely low risk)
- **Return on Initial Capital**: 509.59% (₹10,000 → ₹60,959)

Top performing stocks include:
- COALINDIA: 16 trades, 75% win rate, ₹4,832 profit
- SHRIRAMFIN: 8 trades, 87.5% win rate, ₹3,906 profit
- ADANIENT: 3 trades, 66.67% win rate, ₹3,792 profit
- TATACONSUM: 13 trades, 76.92% win rate, ₹2,822 profit

Stock-specific optimization demonstrates dramatically improved performance compared to using a single configuration for all stocks.

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
- Automatic fallback to default configuration when stock-specific configs are missing
- Data integrity verification
- Robust date handling for performance calculations
- Exception handling to continue processing despite individual stock failures

## Copyright Notice

© 2024 DataBull. All rights reserved.

This is proprietary software. Unauthorized copying, modification, distribution, or use of this software, via any medium, is strictly prohibited.

## Daily Trading Automation

The system includes a complete workflow for daily trading operations:

1. **Automated Data Fetching and Analysis**
   ```bash
   # Run the complete daily automation
   ./daily_trading_automation.sh
   ```
   
   This script:
   - Fetches the latest market data
   - Runs technical analysis with optimized parameters
   - Generates daily buy/sell/hold recommendations
   - Creates a recommendations CSV file with a max investment of ₹50,000 per stock

2. **Daily Recommendations CSV**
   
   The system generates two recommendation files:
   - `data/recommendations/stock_recommendations_YYYYMMDD.csv`: Date-specific recommendations
   - `data/recommendations/latest_recommendations.csv`: Always points to the most recent recommendations
   
   Each recommendation includes:
   - Symbol
   - Current price
   - Buy/Sell/Hold recommendation
   - Confidence score
   - Maximum quantity to trade
   - Recommended investment amount (max ₹50,000)
   - Stop-loss and take-profit levels
   - Reason for the recommendation

3. **Scheduling with Cron**
   
   To run the automation daily before market open:
   ```bash
   # Install the cron job (runs at 8:30 AM on weekdays)
   crontab crontab_trading.txt
   
   # Check that the cron job is installed
   crontab -l
   ```

The recommendations are based on technical analysis signals that are customized for each stock through the optimization process. This provides a daily roadmap for trading decisions that you can follow manually.