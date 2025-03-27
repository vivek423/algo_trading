#!/bin/bash

# Script to optimize all Nifty 100 stocks using the trading configuration file
# WARNING: This script will take a very long time to run (potentially days)
# For more manageable optimization, use optimize_stocks_batch.sh instead

# Get the project root directory (parent of the scripts directory)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Input directory with historical stock data
INPUT_DIR="${PROJECT_ROOT}/data/inputs"

# Trading configuration file - using the default configuration file which now contains Nifty 100 stocks
TRADING_CONFIG="${PROJECT_ROOT}/config/trading_config.yaml"

# List of all Nifty 100 stocks (extracted from trading configuration)
STOCKS=(
    "ADANIENT" "ADANIPORTS" "APOLLOHOSP" "ASIANPAINT" "AXISBANK" "BAJAJ-AUTO" 
    "BAJFINANCE" "BAJAJFINSV" "BPCL" "BHARTIARTL" "BRITANNIA" "CIPLA" 
    "COALINDIA" "DIVISLAB" "DRREDDY" "EICHERMOT" "GRASIM" "HCLTECH" 
    "HDFCBANK" "HDFCLIFE" "HEROMOTOCO" "HINDALCO" "HINDUNILVR" "ICICIBANK" 
    "INDUSINDBK" "INFY" "ITC" "JSWSTEEL" "KOTAKBANK" "LT" "M&M" "MARUTI" 
    "NESTLEIND" "NTPC" "ONGC" "POWERGRID" "RELIANCE" "SBILIFE" "SBIN" 
    "SUNPHARMA" "TCS" "TATACONSUM" "TATAMOTORS" "TATASTEEL" "TECHM" 
    "TITAN" "ULTRACEMCO" "UPL" "WIPRO" "BHEL" "NMDC" "BANKBARODA" "CANBK" 
    "PNB" "IDFC" "BIOCON" "SAIL" "PFC" "RECLTD" "GAIL" "JINDALSTEL" 
    "VEDL" "IDFCFIRSTB" "HAVELLS" "GODREJCP" "MARICO" "DABUR" "ICICIGI" 
    "HDFCAMC" "NAUKRI" "ADANIGREEN" "PAGEIND" "PIDILITIND" "LUPIN" "SIEMENS" 
    "DLF" "SRTRANSFIN" "INDUSTOWER" "INDIGO" "COLPAL" "GODREJPROP" "CHOLAFIN" 
    "BOSCHLTD" "PIIND" "BERGEPAINT" "SRF" "TVSMOTOR" "TRENT" "MPHASIS" 
    "MUTHOOTFIN" "ZYDUSLIFE" "GLAND" "ZOMATO" "APOLLOTYRE" "L&TFH" "BEL" 
    "HONAUT" "AARTIIND" "LICI" "LTIM" "ABBOTINDIA" "ABCAPITAL"
)

# Total number of stocks
TOTAL_STOCKS=${#STOCKS[@]}

# Function to run optimization for a single stock
optimize_stock() {
    local stock=$1
    local index=$2
    
    echo "[$index/$TOTAL_STOCKS] Starting optimization for $stock"
    
    python "${PROJECT_ROOT}/scripts/stock_grid_search.py" \
        --input-dir "$INPUT_DIR" \
        --trading-config "$TRADING_CONFIG" \
        --stocks "$stock" \
        --max-combinations 10000 \
        --max-investment 200000 \
        --initial-capital 1000000 \
        --metric sharpe_ratio
    
    echo "[$index/$TOTAL_STOCKS] Completed optimization for $stock"
    echo "----------------------------------------"
}

# Record start time
START_TIME=$(date +%s)
echo "Starting optimization for all $TOTAL_STOCKS Nifty 100 stocks at $(date)"
echo "This process will take a very long time to complete - potentially days"
echo "For a more manageable approach, consider optimizing in smaller batches"
echo "----------------------------------------"

# Process each stock
for (( i=0; i<$TOTAL_STOCKS; i++ )); do
    stock="${STOCKS[$i]}"
    index=$((i+1))
    optimize_stock "$stock" $index
    
    # Calculate and display progress
    progress=$((index * 100 / TOTAL_STOCKS))
    echo "Overall Progress: $progress% ($index/$TOTAL_STOCKS stocks complete)"
    echo "----------------------------------------"
done

# Record end time and calculate total duration
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
HOURS=$((DURATION / 3600))
MINUTES=$(( (DURATION % 3600) / 60 ))
SECONDS=$((DURATION % 60))

echo "Optimization of all Nifty 100 stocks completed!"
echo "Total time: $HOURS hours, $MINUTES minutes, $SECONDS seconds"
echo "Results saved to data/outputs/stock_grid_search"
echo "Stock-specific configuration files are created in config/stock_configs/" 