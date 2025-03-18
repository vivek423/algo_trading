#!/bin/bash

# daily_trading_automation.sh
# Automated script for daily trading operations
# This script:
# 1. Fetches latest market data
# 2. Generates trading recommendations
# 3. Creates a daily CSV with buy/sell/hold recommendations

# Load environment variables if needed
if [ -f .env ]; then
    source .env
fi

# Activate virtual environment if needed
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Set working directory
cd "$(dirname "$0")"

# Directories
LOG_DIR="logs"
RECOMMENDATIONS_DIR="data/recommendations"

# Create directories if they don't exist
mkdir -p "$LOG_DIR"
mkdir -p "$RECOMMENDATIONS_DIR"

# Log file
TIMESTAMP=$(date +"%Y%m%d")
LOG_FILE="${LOG_DIR}/trading_${TIMESTAMP}.log"

# Start logging
echo "========================================" | tee -a "$LOG_FILE"
echo "Daily trading automation started at $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Step 1: Fetch the latest market data
echo "Fetching latest market data..." | tee -a "$LOG_FILE"
python scripts/data_fetcher.py 2>&1 | tee -a "$LOG_FILE"

# Check if data fetching was successful
if [ $? -ne 0 ]; then
    echo "ERROR: Data fetching failed" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 2: Generate recommendations
echo "Generating trading recommendations..." | tee -a "$LOG_FILE"
python scripts/generate_recommendations.py \
    --input-dir data/inputs \
    --output-dir "$RECOMMENDATIONS_DIR" \
    --trading-config config/trading_config.yaml \
    2>&1 | tee -a "$LOG_FILE"

# Check if recommendations were generated
if [ $? -ne 0 ]; then
    echo "ERROR: Recommendation generation failed" | tee -a "$LOG_FILE"
    exit 1
fi

# Check if the recommendations file exists
RECOMMENDATIONS_FILE="${RECOMMENDATIONS_DIR}/stock_recommendations_${TIMESTAMP}.csv"
LATEST_FILE="${RECOMMENDATIONS_DIR}/latest_recommendations.csv"

if [ -f "$LATEST_FILE" ]; then
    echo "Recommendations generated successfully." | tee -a "$LOG_FILE"
    
    # Count recommendations by type
    BUY_COUNT=$(grep -c "BUY" "$LATEST_FILE")
    SELL_COUNT=$(grep -c "SELL" "$LATEST_FILE")
    TOTAL=$(wc -l < "$LATEST_FILE")
    TOTAL=$((TOTAL - 1))  # Adjust for header row
    
    echo "Today's Recommendations:" | tee -a "$LOG_FILE"
    echo "- Total: $TOTAL" | tee -a "$LOG_FILE"
    echo "- Buy: $BUY_COUNT" | tee -a "$LOG_FILE"
    echo "- Sell: $SELL_COUNT" | tee -a "$LOG_FILE"
    echo "- Hold: $((TOTAL - BUY_COUNT - SELL_COUNT))" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo "Recommendations saved to: $LATEST_FILE" | tee -a "$LOG_FILE"
else
    echo "WARNING: No recommendations file generated" | tee -a "$LOG_FILE"
fi

echo "========================================" | tee -a "$LOG_FILE"
echo "Daily trading automation completed at $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Deactivate virtual environment if it was activated
if [ -d ".venv" ]; then
    deactivate 2>/dev/null
fi

exit 0 