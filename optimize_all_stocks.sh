#!/bin/bash

# Script to optimize all 50 stocks with 10,000 combinations each
# WARNING: This script will take a very long time to run (potentially days)
# For more manageable optimization, use optimize_stocks_batch.sh instead

# Input directory with individual stock files
INPUT_DIR="data/inputs"

# Output directory for results
OUTPUT_DIR="logs/optimization_10000"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# List of all 50 stocks
STOCKS=(
    "ADANIENT" "RELIANCE" "TATAMOTORS" "TCS" "APOLLOHOSP" "ASIANPAINT" 
    "AXISBANK" "BAJAJ-AUTO" "BAJAJFINSV" "BAJFINANCE" "BHARTIARTL" "BEL" 
    "BPCL" "BRITANNIA" "CIPLA" "COALINDIA" "DRREDDY" "EICHERMOT" "GRASIM" 
    "HCLTECH" "HDFCBANK" "HDFCLIFE" "HEROMOTOCO" "HINDALCO" "HINDUNILVR" 
    "ICICIBANK" "INDUSINDBK" "INFY" "ITC" "JSWSTEEL" "KOTAKBANK" "LT" 
    "M&M" "MARUTI" "NESTLEIND" "NTPC" "ONGC" "POWERGRID" "SBILIFE" "SBIN" 
    "SHRIRAMFIN" "SUNPHARMA" "TATACONSUM" "TATASTEEL" "TECHM" "TITAN" 
    "TRENT" "ULTRACEMCO" "WIPRO" "ADANIPORTS"
)

# Total number of stocks
TOTAL_STOCKS=${#STOCKS[@]}

# Function to run optimization for a single stock
optimize_stock() {
    local stock=$1
    local index=$2
    
    echo "[$index/$TOTAL_STOCKS] Starting optimization for $stock with 10,000 combinations"
    
    python scripts/stock_grid_search.py \
        --input-dir "$INPUT_DIR" \
        --output "$OUTPUT_DIR" \
        --stocks "$stock" \
        --max-combinations 10000 \
        --max-investment 5000 \
        --initial-capital 10000 \
        --metric sharpe_ratio
    
    echo "[$index/$TOTAL_STOCKS] Completed optimization for $stock"
    echo "----------------------------------------"
}

# Record start time
START_TIME=$(date +%s)
echo "Starting optimization for all $TOTAL_STOCKS stocks at $(date)"
echo "This process will take a very long time to complete - potentially days"
echo "For a more manageable approach, consider using optimize_stocks_batch.sh instead"
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

echo "Optimization of all stocks completed!"
echo "Total time: $HOURS hours, $MINUTES minutes, $SECONDS seconds"
echo "Results saved to $OUTPUT_DIR" 