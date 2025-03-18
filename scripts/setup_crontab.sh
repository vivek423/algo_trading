#!/bin/bash
#
# Set up crontab from template
#
# This script generates a crontab configuration file from the template,
# replacing placeholders with actual values, and offers to install it.

# Get project root directory (parent of the directory containing this script)
PROJECT_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
TEMPLATE_FILE="${PROJECT_PATH}/crontab_config_template.txt"
OUTPUT_FILE="${PROJECT_PATH}/crontab_config.txt"

# Get Python executable path
PYTHON_PATH=$(which python)
if [ -z "$PYTHON_PATH" ]; then
    # Try python3 if python is not found
    PYTHON_PATH=$(which python3)
    if [ -z "$PYTHON_PATH" ]; then
        echo "Error: Could not find python or python3 executable"
        exit 1
    fi
fi

echo "Setting up crontab for algorithmic trading system..."
echo "Project path: ${PROJECT_PATH}"
echo "Python path: ${PYTHON_PATH}"

# Check if template exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "Error: Template file not found at ${TEMPLATE_FILE}"
    exit 1
fi

# Generate crontab file from template
echo "Generating crontab configuration..."
sed -e "s|{{PROJECT_PATH}}|${PROJECT_PATH}|g" -e "s|{{PYTHON_PATH}}|${PYTHON_PATH}|g" "$TEMPLATE_FILE" > "$OUTPUT_FILE"

echo "Crontab configuration has been generated at: ${OUTPUT_FILE}"

# Ask if user wants to install the crontab
read -p "Do you want to install this crontab now? (y/n) " -n 1 -r
echo    # Move to a new line
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Backup existing crontab
    crontab -l > "${PROJECT_PATH}/crontab_backup.txt" 2>/dev/null || echo "No existing crontab to backup."
    
    # Install new crontab
    crontab "$OUTPUT_FILE"
    
    echo "Crontab installed successfully!"
    echo "A backup of your previous crontab (if any) was saved to: ${PROJECT_PATH}/crontab_backup.txt"
else
    echo "Crontab was not installed. You can install it manually with: crontab ${OUTPUT_FILE}"
fi

echo "Done!" 