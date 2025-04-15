#!/usr/bin/env python3
import os
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from twilio.rest import Client
import pandas as pd
from datetime import datetime
import pytz
from setup_logging import setup_logging
import time

# Configure logging
logger = setup_logging("whatsapp_notifier")

class WhatsAppNotifier:
    """
    WhatsApp notification service using Twilio API.
    
    Requires the following environment variables:
    - TWILIO_ACCOUNT_SID: Your Twilio account SID
    - TWILIO_AUTH_TOKEN: Your Twilio auth token
    - TWILIO_FROM_NUMBER: Your Twilio WhatsApp number (format: whatsapp:+1234567890)
    - TWILIO_TO_NUMBER: Your personal WhatsApp number to receive alerts (format: whatsapp:+1234567890)
    """
    
    def __init__(self, env_file: str = '.env'):
        """
        Initialize WhatsApp notifier with Twilio credentials.
        
        Args:
            env_file: Path to .env file containing Twilio credentials
        """
        # Load environment variables from .env file
        load_dotenv(env_file)
        
        # Get Twilio credentials from environment variables
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.from_number = os.getenv('TWILIO_FROM_NUMBER')
        self.to_number = os.getenv('TWILIO_TO_NUMBER')
        
        # Validate required credentials
        if not all([self.account_sid, self.auth_token, self.from_number, self.to_number]):
            missing = []
            if not self.account_sid: missing.append('TWILIO_ACCOUNT_SID')
            if not self.auth_token: missing.append('TWILIO_AUTH_TOKEN')
            if not self.from_number: missing.append('TWILIO_FROM_NUMBER')
            if not self.to_number: missing.append('TWILIO_TO_NUMBER')
            
            error_msg = f"Missing Twilio credentials: {', '.join(missing)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Ensure WhatsApp format for phone numbers
        if not self.from_number.startswith('whatsapp:'):
            self.from_number = f"whatsapp:{self.from_number}"
        
        if not self.to_number.startswith('whatsapp:'):
            self.to_number = f"whatsapp:{self.to_number}"
        
        # Initialize Twilio client
        self.client = Client(self.account_sid, self.auth_token)
        logger.info("WhatsApp notifier initialized successfully")
    
    def send_recommendation_alert(self, recommendations: List[Dict[str, Any]]) -> bool:
        """
        Send stock recommendations via WhatsApp in batches of 5 stocks per message.
        
        Args:
            recommendations: List of stock recommendation dictionaries
            
        Returns:
            bool: True if all messages were sent successfully, False if any failed
        """
        if not recommendations:
            logger.warning("No recommendations to send")
            return False
        
        # Get current date and time header
        ist_now = datetime.now(pytz.timezone('Asia/Kolkata'))
        header = "🚨 *STOCK RECOMMENDATIONS* 🚨\n\n"
        header += f"*Date:* {ist_now.strftime('%Y-%m-%d')}\n"
        header += f"*Time:* {ist_now.strftime('%H:%M:%S')}\n\n"
        
        # Split recommendations into batches of 5
        batch_size = 5
        success = True
        total_batches = (len(recommendations) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min((batch_num + 1) * batch_size, len(recommendations))
            batch = recommendations[start_idx:end_idx]
            
            # Construct message body for this batch
            message_body = header
            if total_batches > 1:
                message_body += f"*Batch {batch_num + 1} of {total_batches}*\n\n"
            
            # Add each recommendation in this batch
            for i, rec in enumerate(batch, start=start_idx + 1):
                symbol = rec.get('symbol', 'UNKNOWN')
                close_price = rec.get('close', 0.0)
                quantity = rec.get('quantity', 0)
                stop_loss = rec.get('stop_loss', 0.0)
                take_profit = rec.get('take_profit', 0.0)
                
                message_body += f"*{i}. {symbol}*\n"
                message_body += f"   💰 Price: ₹{close_price:.2f}\n"
                message_body += f"   🔢 Quantity: {quantity}\n"
                message_body += f"   🛑 Stop Loss: ₹{stop_loss:.2f}\n"
                message_body += f"   🎯 Take Profit: ₹{take_profit:.2f}\n"
                
                # Calculate potential profit and loss
                potential_profit = (take_profit - close_price) * quantity
                potential_loss = (close_price - stop_loss) * quantity
                
                message_body += f"   📈 Potential Profit: ₹{potential_profit:.2f}\n"
                message_body += f"   📉 Max Loss: ₹{potential_loss:.2f}\n\n"
            
            # Add footer
            message_body += "🤖 *Generated by Algo Trading Bot* 🤖"
            
            # Send this batch
            if not self.send_simple_message(message_body):
                logger.error(f"Failed to send batch {batch_num + 1} of {total_batches}")
                success = False
            else:
                logger.info(f"Successfully sent batch {batch_num + 1} of {total_batches} ({len(batch)} stocks)")
            
            # Add a small delay between batches to avoid rate limiting
            if batch_num < total_batches - 1:
                time.sleep(1)
        
        return success
    
    def send_trading_summary(self, date: Optional[str] = None) -> bool:
        """
        Send end-of-day trading summary via WhatsApp.
        
        Args:
            date: Date for the summary in YYYY-MM-DD format. If None, uses today's date.
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        # Get today's recommendations file
        if date is None:
            ist_timezone = pytz.timezone('Asia/Kolkata')
            date = datetime.now(ist_timezone).strftime('%Y-%m-%d')
        
        date_for_file = date.replace('-', '')
        recommendations_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                         'data', 'outputs', 'recommendations')
        recommendations_file = os.path.join(recommendations_dir, f'stock_recommendations_{date_for_file}.csv')
        
        # Check if recommendations file exists
        if not os.path.exists(recommendations_file):
            logger.warning(f"No recommendations file found for {date}")
            message_body = f"📊 *TRADING SUMMARY: {date}* 📊\n\n"
            message_body += "No trading activity was recorded for today.\n\n"
            message_body += "🤖 *Generated by Algo Trading Bot* 🤖"
            return self.send_simple_message(message_body)
        
        try:
            # Load recommendations data
            recommendations_df = pd.read_csv(recommendations_file)
            
            # Begin constructing message
            message_body = f"📊 *TRADING SUMMARY: {date}* 📊\n\n"
            
            # Calculate statistics
            total_recommendations = len(recommendations_df)
            
            # Map signal_combined to recommendation type (1 = BUY, -1 = SELL, 0 = HOLD)
            if 'signal_combined' in recommendations_df.columns:
                recommendations_df['recommendation'] = recommendations_df['signal_combined'].apply(
                    lambda x: 'BUY' if x == 1 else ('SELL' if x == -1 else 'HOLD'))
            else:
                # Default all to BUY if signal_combined not present
                recommendations_df['recommendation'] = 'BUY'
            
            # Count by recommendation type
            buy_signals = len(recommendations_df[recommendations_df['recommendation'] == 'BUY'])
            sell_signals = len(recommendations_df[recommendations_df['recommendation'] == 'SELL'])
            hold_signals = len(recommendations_df[recommendations_df['recommendation'] == 'HOLD'])
            
            # Calculate total potential investment for BUY signals
            # If quantity and close exist, calculate investment amount
            if 'quantity' in recommendations_df.columns and 'close' in recommendations_df.columns:
                recommendations_df['investment_amount'] = recommendations_df['quantity'] * recommendations_df['close']
                buy_investment = recommendations_df[recommendations_df['recommendation'] == 'BUY']['investment_amount'].sum()
            else:
                buy_investment = 0.0
            
            # Add summary statistics
            message_body += f"*Total Stocks Analyzed:* {total_recommendations}\n"
            message_body += f"*Buy Signals:* {buy_signals}\n"
            message_body += f"*Sell Signals:* {sell_signals}\n"
            message_body += f"*Hold Signals:* {hold_signals}\n\n"
            
            if buy_signals > 0:
                message_body += f"*Total Potential Investment:* ₹{buy_investment:,.2f}\n\n"
                
                # Add details of stocks with BUY recommendation
                message_body += "*BUY Recommendations:*\n"
                buy_stocks = recommendations_df[recommendations_df['recommendation'] == 'BUY']
                
                for i, (_, row) in enumerate(buy_stocks.iterrows(), 1):
                    symbol = row['symbol']
                    close_price = row['close']
                    quantity = row['quantity'] if 'quantity' in row else 0
                    investment = close_price * quantity
                    
                    message_body += f"{i}. *{symbol}*: ₹{close_price:.2f} × {quantity} units\n"
                    message_body += f"   Investment: ₹{investment:,.2f}\n"
                    
                    if 'stop_loss' in row and 'take_profit' in row and pd.notna(row['stop_loss']) and pd.notna(row['take_profit']):
                        potential_profit = (row['take_profit'] - close_price) * quantity
                        potential_loss = (close_price - row['stop_loss']) * quantity
                        
                        message_body += f"   Potential Profit: ₹{potential_profit:,.2f}\n"
                        message_body += f"   Max Loss: ₹{potential_loss:,.2f}\n"
                    
                    message_body += "\n"
            
            if sell_signals > 0:
                message_body += "*SELL Recommendations:*\n"
                sell_stocks = recommendations_df[recommendations_df['recommendation'] == 'SELL']
                
                for i, (_, row) in enumerate(sell_stocks.iterrows(), 1):
                    message_body += f"{i}. *{row['symbol']}*: ₹{row['close']:.2f}\n"
                
                message_body += "\n"
            
            # Add footer
            message_body += "🤖 *Generated by Algo Trading Bot* 🤖"
            
            # Send WhatsApp message
            return self.send_simple_message(message_body)
            
        except Exception as e:
            logger.error(f"Error generating trading summary: {str(e)}")
            return False
    
    def send_simple_message(self, message_body: str) -> bool:
        """
        Send a simple WhatsApp message.
        
        Args:
            message_body: Text content of the message
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        try:
            # Send message via Twilio
            message = self.client.messages.create(
                from_=self.from_number,
                body=message_body,
                to=self.to_number
            )
            
            logger.info(f"WhatsApp message sent successfully (SID: {message.sid})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {str(e)}")
            return False


# Test code (runs when script is executed directly)
if __name__ == "__main__":
    # Configure logging for testing is already done above
    try:
        # Initialize notifier
        notifier = WhatsAppNotifier()
        
        # Test sending a daily summary
        success = notifier.send_trading_summary()
        
        if success:
            print("Trading summary sent successfully!")
        else:
            print("Failed to send trading summary")
            
    except Exception as e:
        print(f"Error during test: {str(e)}") 