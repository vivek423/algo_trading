# Setting Up WhatsApp Notifications for Stock Recommendations

This guide will help you set up WhatsApp notifications for your algorithmic trading system. Every time the system identifies a potential buy signal for a stock, you'll receive a WhatsApp message with the details.

## Prerequisites

1. A Twilio account (free trial available)
2. Your personal WhatsApp account
3. Python packages: `twilio` and `python-dotenv` (included in requirements.txt)

## Step 1: Sign Up for Twilio

1. Go to [Twilio's website](https://www.twilio.com/try-twilio) and create an account
2. During sign-up, you'll need to verify your email and phone number
3. Once registered, you'll be given a free trial account with credit to start using the service

## Step 2: Set Up the WhatsApp Sandbox

1. In your Twilio console, navigate to "Messaging" > "Try it out" > "Send a WhatsApp message"
2. Follow the instructions to join your Twilio Sandbox for WhatsApp:
   - Send a WhatsApp message to the Twilio number shown on the page
   - Use the exact join code provided (e.g., "join <something>")
3. Once connected, you'll receive a confirmation message

## Step 3: Configure Your Environment Variables

1. Copy the `.env.sample` file to a new file named `.env`:
   ```bash
   cp .env.sample .env
   ```

2. Edit the `.env` file with your Twilio credentials:
   ```
   TWILIO_ACCOUNT_SID=your_account_sid_here
   TWILIO_AUTH_TOKEN=your_auth_token_here
   TWILIO_FROM_NUMBER=+14155238886  # This is your Twilio WhatsApp number
   TWILIO_TO_NUMBER=+919876543210   # Your personal WhatsApp number
   ```

   Find your Account SID and Auth Token in the Twilio Console dashboard.

## Step 4: Test the WhatsApp Notifier

Run the WhatsApp notifier test script to ensure everything is working:

```bash
python scripts/whatsapp_notifier.py
```

If successful, you should receive a test WhatsApp message on your phone.

## Step 5: Enable Notifications in the Recommendation Generator

When running the recommendation generator, add the `--notifications` flag:

```bash
python scripts/generate_recommendations.py --notifications
```

## Step 6: Update Crontab (Optional)

If you want automatic notifications, ensure your crontab entries include the `--notifications` flag:

```bash
crontab crontab_config_with_recommendations.txt
```

## Troubleshooting

### Not Receiving Messages?

1. **Check Sandbox Status**: Ensure you've properly joined the Twilio Sandbox for WhatsApp
2. **Check Credentials**: Verify your Account SID and Auth Token are correct
3. **Check Logs**: Look at the logs in `logs/recommendations.log` for any error messages
4. **Sandbox Expiration**: Twilio's WhatsApp Sandbox connections expire after 72 hours of inactivity. If it's been a while, you may need to rejoin the sandbox.

### Trial Account Limitations

1. With a trial account, you can only send WhatsApp messages to the verified phone number you used during signup
2. Trial accounts have a credit limit and usage restrictions
3. For production use, you'll need to upgrade to a paid Twilio account

## Upgrading to Production (Optional)

For a more robust solution:

1. **Upgrade to a Paid Twilio Account**: This removes trial limitations
2. **Apply for a WhatsApp Business API Account**: For higher volume and more features
3. **Add Error Handling and Retries**: Enhance the notification system to handle connection issues

## Privacy and Security Notes

1. Your WhatsApp number and Twilio credentials are sensitive information
2. Never commit the `.env` file to version control
3. Consider using a dedicated WhatsApp number for this purpose rather than your primary number 