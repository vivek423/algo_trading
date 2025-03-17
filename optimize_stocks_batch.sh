#!/bin/bash

# Script to optimize stocks in batches with 10,000 combinations each
# Usage: ./optimize_stocks_batch.sh [start_index] [end_index]
# Example: ./optimize_stocks_batch.sh 0 9  # Process the first 10 stocks

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

# Get the start and end indices from command line arguments
START_INDEX=${1:-0}  # Default to 0 if not provided
END_INDEX=${2:-$((${#STOCKS[@]}-1))}  # Default to the last stock if not provided

# Make sure indices are within valid range
if [ $START_INDEX -lt 0 ] || [ $START_INDEX -ge ${#STOCKS[@]} ]; then
    echo "Error: Start index out of range (0-$((${#STOCKS[@]}-1)))"
    exit 1
fi

if [ $END_INDEX -lt 0 ] || [ $END_INDEX -ge ${#STOCKS[@]} ]; then
    echo "Error: End index out of range (0-$((${#STOCKS[@]}-1)))"
    exit 1
fi

if [ $START_INDEX -gt $END_INDEX ]; then
    echo "Error: Start index must be less than or equal to end index"
    exit 1
fi

# Calculate number of stocks to process
NUM_STOCKS=$((END_INDEX - START_INDEX + 1))

# Function to run optimization for a single stock
optimize_stock() {
    local stock=$1
    local index=$2
    local total=$3
    
    echo "[$index/$total] Starting optimization for $stock with 10,000 combinations"
    
    python scripts/stock_grid_search.py \
        --input-dir "$INPUT_DIR" \
        --output "$OUTPUT_DIR" \
        --stocks "$stock" \
        --max-combinations 10000 \
        --max-investment 5000 \
        --initial-capital 10000 \
        --metric sharpe_ratio
    
    echo "[$index/$total] Completed optimization for $stock"
    echo "----------------------------------------"
}

# Record start time
START_TIME=$(date +%s)
echo "Starting optimization for batch of $NUM_STOCKS stocks at $(date)"
echo "Processing stocks from ${STOCKS[$START_INDEX]} to ${STOCKS[$END_INDEX]}"
echo "This process will take a long time to complete"
echo "----------------------------------------"

# Process each stock in the specified range
COUNTER=1
for (( i=$START_INDEX; i<=$END_INDEX; i++ )); do
    optimize_stock "${STOCKS[$i]}" $COUNTER $NUM_STOCKS
    COUNTER=$((COUNTER + 1))
    
    # Calculate and display progress
    progress=$(( (COUNTER - 1) * 100 / NUM_STOCKS ))
    echo "Batch Progress: $progress% ($((COUNTER-1))/$NUM_STOCKS stocks complete)"
    echo "----------------------------------------"
done

# Record end time and calculate total duration
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
HOURS=$((DURATION / 3600))
MINUTES=$(( (DURATION % 3600) / 60 ))
SECONDS=$((DURATION % 60))

echo "Batch optimization completed!"
echo "Processed stocks from index $START_INDEX to $END_INDEX"
echo "Total time: $HOURS hours, $MINUTES minutes, $SECONDS seconds"
echo "Results saved to $OUTPUT_DIR" 