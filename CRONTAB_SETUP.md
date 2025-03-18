# Setting Up Automated Stock Trading Schedules

This guide explains how to set up the cron jobs that power the automated stock trading system.

## What Does the Crontab Do?

The crontab configuration schedules the following tasks:

1. **Data Fetcher** (`scripts/data_fetcher.py`)
   - Runs hourly from 9:17 AM to 4:17 PM on weekdays (market hours)
   - Collects the latest stock price data for all configured stocks
   - Performs an end-of-day run at 4:30 PM

2. **Recommendation Generator** (`scripts/generate_recommendations.py`)
   - Runs 5 minutes after each data fetch (9:22 AM to 4:22 PM)
   - Analyzes stocks for buy signals based on technical indicators
   - Sends WhatsApp notifications when buy signals are detected
   - Performs an end-of-day run at 4:35 PM

3. **Cron Job Monitor** (`scripts/check_cron.py`)
   - Runs daily at 10:00 AM
   - Verifies that all scheduled jobs are running properly

## Automatic Setup (Recommended)

The easiest way to set up the crontab is using the provided setup script:

1. Navigate to your project directory
2. Run the setup script:
   ```bash
   ./scripts/setup_crontab.sh
   ```
3. When prompted, type `y` to install the crontab

The script will:
- Detect your project path automatically
- Generate the proper crontab configuration
- Backup your existing crontab (if any)
- Install the new crontab

## Manual Setup

If you prefer to set up the crontab manually:

1. Copy the template file to create your configuration:
   ```bash
   cp crontab_config_template.txt crontab_config.txt
   ```

2. Edit the new file to replace `{{PROJECT_PATH}}` with your actual project path:
   ```bash
   sed -i '' "s|{{PROJECT_PATH}}|$(pwd)|g" crontab_config.txt
   ```

3. Install the crontab:
   ```bash
   crontab crontab_config.txt
   ```

## Verifying the Installation

To verify that your crontab was installed correctly:

```bash
crontab -l
```

This should display the installed crontab configuration.

## Customizing the Schedule

If you need to modify the schedule:

1. Edit the `crontab_config_template.txt` file
2. Run the setup script again to regenerate and install the updated crontab

## Maintaining in Version Control

For version control:

- Commit the `crontab_config_template.txt` file (contains placeholders)
- DO NOT commit the generated `crontab_config.txt` file (contains machine-specific paths)
- Add `crontab_config.txt` to your `.gitignore` file

## Troubleshooting

If you encounter issues with your scheduled tasks:

1. Check the log files in the `logs/` directory
2. Verify that the crontab is installed: `crontab -l`
3. Make sure the scripts have execution permissions: `chmod +x scripts/*.py`
4. Ensure your environment variables are properly set up in your `.env` file 