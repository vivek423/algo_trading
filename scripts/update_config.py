#!/usr/bin/env python3
import yaml
import os
import argparse
import logging
import sys
from setup_logging import setup_script_logging

# Configure logging
logger = setup_script_logging()

def update_config(results_file, config_file, metric='sharpe_ratio'):
    """
    Update technical indicators configuration with best parameters from grid search.
    
    Args:
        results_file: Path to the grid search results file (top_configurations.yaml)
        config_file: Path to the technical indicators configuration file to update
        metric: Metric to sort by ('sharpe_ratio', 'cagr', or 'win_rate')
    """
    try:
        # Load grid search results
        with open(results_file, 'r') as f:
            results = yaml.safe_load(f)
        
        logger.info(f"Loaded {len(results)} configurations from {results_file}")
        
        # Sort results by the specified metric
        if metric == 'sharpe_ratio':
            # Higher sharpe ratio is better, but could be negative
            results.sort(key=lambda x: x['sharpe_ratio'], reverse=True)
        elif metric == 'cagr':
            # Higher CAGR is better
            results.sort(key=lambda x: x['cagr'], reverse=True)
        elif metric == 'win_rate':
            # Higher win rate is better
            results.sort(key=lambda x: x['win_rate'], reverse=True)
        else:
            raise ValueError(f"Invalid metric: {metric}")
        
        # Get the best configuration
        best_config = results[0]
        best_params = best_config['parameters']
        
        logger.info(f"Best {metric}: {best_config[metric]}")
        logger.info(f"Other metrics - CAGR: {best_config['cagr']:.2f}%, Win Rate: {best_config['win_rate']:.2f}%")
        
        # Load current config
        current_config = {}
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                current_config = yaml.safe_load(f)
        
        # Update with best parameters
        for section, params in best_params.items():
            if section not in current_config:
                current_config[section] = {}
            for param, value in params.items():
                current_config[section][param] = value
        
        # Ensure columns section exists
        if 'columns' not in current_config:
            current_config['columns'] = {
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'timestamp': 'timestamp'
            }
        
        # Create a formatted config with comments
        formatted_config = """# Technical Analysis Parameters - Optimized via Grid Search

# MACD Parameters
macd:
  fast_period: {macd_fast}
  slow_period: {macd_slow}
  signal_period: {macd_signal}

# Support and Resistance Parameters
support_resistance:
  support_period: {support_period}
  resistance_period: {resistance_period}

# ATR Parameters
atr:
  window: {atr_window}

# EMA Parameters
ema:
  period: {ema_period}

# Bollinger Bands Parameters
bollinger_bands:
  length: {bb_length}
  std: {bb_std}

# RSI Parameters
rsi:
  length: {rsi_length}
  oversold: {rsi_oversold}
  overbought: {rsi_overbought}

# Risk Management Parameters
risk_management:
  stop_loss_atr_multiplier: {sl_multiplier}
  take_profit_atr_multiplier: {tp_multiplier}

# Default column names
columns:
  open: 'open'
  high: 'high'
  low: 'low'
  close: 'close'
  volume: 'volume'
  timestamp: 'timestamp'
""".format(
            macd_fast=best_params['macd']['fast_period'],
            macd_slow=best_params['macd']['slow_period'],
            macd_signal=best_params['macd']['signal_period'],
            support_period=best_params['support_resistance']['support_period'],
            resistance_period=best_params['support_resistance']['resistance_period'],
            atr_window=best_params['atr']['window'],
            ema_period=best_params['ema']['period'],
            bb_length=best_params['bollinger_bands']['length'],
            bb_std=best_params['bollinger_bands']['std'],
            rsi_length=best_params['rsi']['length'],
            rsi_oversold=best_params['rsi']['oversold'],
            rsi_overbought=best_params['rsi']['overbought'],
            sl_multiplier=best_params['risk_management']['stop_loss_atr_multiplier'],
            tp_multiplier=best_params['risk_management']['take_profit_atr_multiplier']
        )
        
        # Write the updated config
        with open(config_file, 'w') as f:
            f.write(formatted_config)
        
        logger.info(f"Updated {config_file} with best parameters")
        logger.info(f"Metric values for best config - Sharpe: {best_config['sharpe_ratio']:.4f}, CAGR: {best_config['cagr']:.2f}%, Win Rate: {best_config['win_rate']:.2f}%")
        
        # Optional: Also save a backup of the previous config
        backup_file = f"{config_file}.bak"
        if os.path.exists(config_file + '.bak'):
            logger.info(f"Backup file {backup_file} already exists, not overwriting")
        else:
            with open(config_file + '.bak', 'w') as f:
                yaml.dump(current_config, f, default_flow_style=False)
            logger.info(f"Saved backup of previous config to {backup_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating configuration: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Update technical indicators configuration with best parameters from grid search')
    parser.add_argument('--results', '-r', default='logs/top_configurations.yaml', 
                        help='Path to grid search results file (top_configurations.yaml)')
    parser.add_argument('--config', '-c', default='config/technical_indicators.yaml',
                        help='Path to technical indicators config file to update')
    parser.add_argument('--metric', '-m', choices=['sharpe_ratio', 'cagr', 'win_rate'], default='sharpe_ratio',
                        help='Metric to optimize for')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.results):
        logger.error(f"Results file not found: {args.results}")
        return 1
    
    success = update_config(args.results, args.config, args.metric)
    
    if success:
        logger.info("Configuration updated successfully")
        
        # Regenerate indicators file using technical_analysis.py with its hardcoded output path
        logger.info("Regenerating indicators file with updated configuration")
        
        # Run the technical_analysis.py script with --all option (which now uses hardcoded output path)
        os.system("python scripts/technical_analysis.py --all")
        
        logger.info("All done! You can now run performance analysis with the updated configuration.")
        return 0
    else:
        logger.error("Failed to update configuration")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 