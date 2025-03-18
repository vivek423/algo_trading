# WhatsApp Trading Notifications

This system integrates WhatsApp notifications to keep you informed about trading opportunities and daily performance summaries.

## Features

### 1. Real-time Buy Signal Notifications

When the system detects buy signals based on your technical analysis parameters, it sends a WhatsApp message containing:

- Stock symbol
- Current price
- Recommended quantity to purchase
- Stop loss price
- Take profit price
- Potential profit and maximum loss calculations

### 2. End-of-Day Trading Summary

Every day at 4:45 PM (after market close), the system sends a comprehensive WhatsApp summary including:

- Total number of stocks analyzed
- Number of buy/sell/hold signals detected
- Total potential investment amount
- Detailed breakdown of buy recommendations
- List of sell recommendations

This end-of-day summary is sent regardless of whether any trades were made, providing you with a complete picture of the day's trading activity.

## Setup Instructions

### 1. Prerequisites

- A Twilio account (free trial available)
- A WhatsApp-enabled phone number

### 2. Twilio Account Setup

1. Sign up at [Twilio](https://www.twilio.com/try-twilio)
2. Activate the WhatsApp Sandbox:
   - Navigate to [Twilio WhatsApp Sandbox](https://www.twilio.com/console/sms/whatsapp/sandbox)
   - Follow the instructions to connect your WhatsApp number to the Sandbox

### 3. Environment Configuration

Create or update your `.env` file with the following Twilio credentials:

```
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_FROM_NUMBER=+14155238886  # Your Twilio WhatsApp Sandbox number
TWILIO_TO_NUMBER=+919876543210   # Your personal WhatsApp number
```

### 4. Install Required Packages

```bash
pip install twilio python-dotenv
```

## Usage

### Manual Notification Testing

You can test the WhatsApp notification system anytime:

```bash
# Test recommendation notifications
python scripts/whatsapp_notifier.py

# Generate recommendations and send notifications if any buy signals are found
python scripts/generate_recommendations.py --notifications

# Send end-of-day summary (without generating new recommendations)
python scripts/generate_recommendations.py --eod-summary --notifications
```

### Automated Notifications

The crontab configuration automatically handles:

1. Sending buy signal notifications throughout the trading day
2. Sending an end-of-day summary at 4:45 PM on trading days

## Troubleshooting

- **No messages received**: Ensure your WhatsApp number is correctly connected to the Twilio Sandbox
- **Error messages**: Check `logs/recommendations.log` for detailed error information
- **Message format issues**: Make sure your Twilio account is active and has available credit

## Privacy and Security Notes

1. Your WhatsApp number and Twilio credentials are sensitive information
2. Never commit the `.env`