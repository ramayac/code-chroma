"""
Centralized configuration management for smart search.
All configuration options are loaded from config.json.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List
from backend.logger import get_logger

logger = get_logger()

class Config:
    _instance = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._load_config()
        return cls._instance
    
    @classmethod
    def _load_config(cls) -> None:
        """Load configuration from config.json"""
        config_path = Path("config.json")
        
        if not config_path.exists():
            raise FileNotFoundError("config.json is mandatory and must exist")
            
        try:
            with open(config_path, 'r') as f:
                cls._config = json.load(f)
            logger.info(f"Configuration loaded from {config_path}")
        except Exception as e:
            logger.error(f"Error loading config.json: {e}")
            raise
    
    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        return cls._config.get(key, default)
    
    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """Get all configuration values"""
        return cls._config.copy()
    
    @classmethod
    def reload(cls) -> None:
        """Reload configuration from file"""
        cls._load_config()
    
    # Convenience properties for commonly used config values
    @property
    def source_folder(self) -> str:
        return self.get("source_folder")
    
    @property
    def index_folder(self) -> str:
        return self.get("index_folder")
    
    @property
    def supported_extensions(self) -> List[str]:
        return self.get("supported_extensions")
    
    @property
    def chunk_size(self) -> int:
        return self.get("chunk_size")
    
    @property
    def chunk_overlap(self) -> int:
        return self.get("chunk_overlap")
    
    @property
    def batch_size(self) -> int:
        return self.get("batch_size")
    
    @property
    def min_search(self) -> float:
        return self.get("min_search")
    
    @property
    def ignore_patterns(self) -> List[str]:
        return self.get("ignore_patterns")


# Global config instance
config = Config()
