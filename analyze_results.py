#!/usr/bin/env python3
import pandas as pd
import numpy as np
import os
import sys

def analyze_performance():
    """Analyze trading performance from trade log"""
    # Load the trade log
    trade_log_path = 'data/analysis/trade_log.csv'
    if not os.path.exists(trade_log_path):
        print(f"Error: Trade log not found at {trade_log_path}")
        sys.exit(1)
        
    trade_log = pd.read_csv(trade_log_path)
    
    # Add is_profitable column based on pnl
    trade_log['is_profitable'] = trade_log['pnl'] > 0
    
    # Basic metrics
    total_trades = len(trade_log)
    win_rate = trade_log['is_profitable'].mean() * 100
    total_pnl = trade_log['pnl'].sum()
    initial_capital = 10000.0
    final_capital = initial_capital + total_pnl
    
    # Stock-specific analysis
    stock_stats = {}
    for symbol, group in trade_log.groupby('symbol'):
        stock_stats[symbol] = {
            'num_trades': len(group),
            'win_rate': group['is_profitable'].mean() * 100,
            'total_pnl': group['pnl'].sum(),
            'avg_pnl_per_trade': group['pnl'].mean(),
            'max_win': group[group['pnl'] > 0]['pnl'].max() if any(group['pnl'] > 0) else 0,
            'max_loss': group[group['pnl'] < 0]['pnl'].min() if any(group['pnl'] < 0) else 0
        }
    
    # Convert to DataFrame for easier sorting
    stats = pd.DataFrame.from_dict(stock_stats, orient='index')
    stats = stats.sort_values('total_pnl', ascending=False)
    
    # Print results
    print(f"\n{'=' * 40}")
    print(f"TRADING PERFORMANCE ANALYSIS")
    print(f"{'=' * 40}")
    
    print(f"\nOVERALL PERFORMANCE:")
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Initial Capital: ₹{initial_capital:,.2f}")
    print(f"Final Capital: ₹{final_capital:,.2f}")
    print(f"Realized P&L: ₹{total_pnl:,.2f}")
    print(f"Return on Capital: {(total_pnl / initial_capital) * 100:.2f}%")
    
    # Print top 10 performing stocks
    print(f"\nTOP 10 PERFORMING STOCKS:")
    top_stocks = stats.head(10)
    for idx, (symbol, row) in enumerate(top_stocks.iterrows(), 1):
        print(f"{idx}. {symbol}: {row['num_trades']} trades, {row['win_rate']:.1f}% win rate, P&L: ₹{row['total_pnl']:,.2f}")
    
    # Print 5 worst performing stocks (if any have negative P&L)
    worst_stocks = stats.tail(5)
    if any(worst_stocks['total_pnl'] < 0):
        print(f"\nBOTTOM 5 PERFORMING STOCKS:")
        for idx, (symbol, row) in enumerate(worst_stocks.iterrows(), 1):
            print(f"{idx}. {symbol}: {row['num_trades']} trades, {row['win_rate']:.1f}% win rate, P&L: ₹{row['total_pnl']:,.2f}")
    
    # Print stocks with highest win rates (at least 2 trades)
    high_win_stocks = stats[stats['num_trades'] >= 2].sort_values('win_rate', ascending=False).head(5)
    print(f"\nTOP 5 STOCKS BY WIN RATE (min 2 trades):")
    for idx, (symbol, row) in enumerate(high_win_stocks.iterrows(), 1):
        print(f"{idx}. {symbol}: {row['num_trades']} trades, {row['win_rate']:.1f}% win rate, P&L: ₹{row['total_pnl']:,.2f}")
    
    # Print stocks with highest average P&L per trade (at least 2 trades)
    high_avg_pnl_stocks = stats[stats['num_trades'] >= 2].sort_values('avg_pnl_per_trade', ascending=False).head(5)
    print(f"\nTOP 5 STOCKS BY AVG P&L PER TRADE (min 2 trades):")
    for idx, (symbol, row) in enumerate(high_avg_pnl_stocks.iterrows(), 1):
        print(f"{idx}. {symbol}: {row['num_trades']} trades, avg P&L: ₹{row['avg_pnl_per_trade']:,.2f}")

if __name__ == "__main__":
    analyze_performance() 