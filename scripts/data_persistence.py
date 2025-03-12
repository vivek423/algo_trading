import os
import pandas as pd
import json
import logging
from typing import Dict, List, Optional
from pathlib import Path
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)

class DataPersistenceChecker:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.metadata_file = os.path.join(data_dir, 'data_metadata.json')
        
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of a file"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
        
    def save_metadata(self, file_path: str, df: pd.DataFrame):
        """Save metadata for a data file"""
        metadata = {
            'file_path': file_path,
            'file_hash': self.calculate_file_hash(file_path),
            'rows': len(df),
            'columns': list(df.columns),
            'start_date': df.index.min().isoformat(),
            'end_date': df.index.max().isoformat(),
            'last_modified': datetime.now().isoformat(),
            'file_size': os.path.getsize(file_path)
        }
        
        all_metadata = self.load_all_metadata()
        all_metadata[file_path] = metadata
        
        with open(self.metadata_file, 'w') as f:
            json.dump(all_metadata, f, indent=2)
            
    def load_all_metadata(self) -> Dict:
        """Load all metadata"""
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {}
        
    def verify_file_integrity(self, file_path: str) -> bool:
        """Verify if a file's current state matches its metadata"""
        try:
            all_metadata = self.load_all_metadata()
            if file_path not in all_metadata:
                logger.error(f"No metadata found for {file_path}")
                return False
                
            metadata = all_metadata[file_path]
            
            # Check if file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False
                
            # Check file hash
            current_hash = self.calculate_file_hash(file_path)
            if current_hash != metadata['file_hash']:
                logger.error(f"File hash mismatch for {file_path}")
                return False
                
            # Check file size
            current_size = os.path.getsize(file_path)
            if current_size != metadata['file_size']:
                logger.error(f"File size mismatch for {file_path}")
                return False
                
            # Load and verify data
            df = pd.read_csv(file_path, index_col='timestamp', parse_dates=True)
            
            # Check row count
            if len(df) != metadata['rows']:
                logger.error(f"Row count mismatch for {file_path}")
                return False
                
            # Check columns
            if list(df.columns) != metadata['columns']:
                logger.error(f"Column mismatch for {file_path}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error verifying file integrity for {file_path}: {str(e)}")
            return False
            
    def verify_all_files(self) -> Dict[str, bool]:
        """Verify integrity of all data files"""
        results = {}
        all_metadata = self.load_all_metadata()
        
        for file_path in all_metadata:
            results[file_path] = self.verify_file_integrity(file_path)
            
        return results
        
    def clean_missing_files(self):
        """Remove metadata for files that no longer exist"""
        all_metadata = self.load_all_metadata()
        existing_files = {
            file_path: metadata 
            for file_path, metadata in all_metadata.items() 
            if os.path.exists(file_path)
        }
        
        with open(self.metadata_file, 'w') as f:
            json.dump(existing_files, f, indent=2)
            
    def get_data_summary(self) -> Dict:
        """Get summary of all persisted data"""
        all_metadata = self.load_all_metadata()
        
        return {
            'total_files': len(all_metadata),
            'total_size': sum(meta['file_size'] for meta in all_metadata.values()),
            'date_range': {
                'start': min(meta['start_date'] for meta in all_metadata.values()),
                'end': max(meta['end_date'] for meta in all_metadata.values())
            },
            'last_update': max(meta['last_modified'] for meta in all_metadata.values())
        } 