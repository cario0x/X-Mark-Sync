import yaml
import os
from typing import Optional

class ConfigManager:
    """
    Manages configuration and sync state.
    """
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = os.path.abspath(config_path)
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """
        Loads config from YAML file. Creates default if not exists.
        """
        if not os.path.exists(self.config_path):
            return self._create_default_config()
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            try:
                return yaml.safe_load(f) or {}
            except yaml.YAMLError:
                return self._create_default_config()

    def _create_default_config(self) -> dict:
        """
        Creates and saves a default configuration.
        """
        default_config = {
            "obsidian_vault_path": "./data/bookmarks",
            "headless_mode": False,
            "max_tweets_limit": 50,
            "sync_state": {
                "last_synced_id": None,
                "last_sync_time": None
            }
        }
        self._save_config(default_config)
        return default_config

    def _save_config(self, config_data: dict = None):
        """
        Saves the current config to file.
        """
        if config_data is None:
            config_data = self.config
            
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, sort_keys=False)

    def get(self, key: str, default=None):
        """
        Get a config value.
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        """
        Sets a config value and saves to file.
        """
        self.config[key] = value
        self._save_config()

    def get_last_synced_id(self) -> Optional[str]:
        """
        Returns the ID of the last successfully synced tweet.
        """
        return self.config.get("sync_state", {}).get("last_synced_id")

    def update_last_synced_id(self, tweet_id: str):
        """
        Updates the last synced ID and saves config.
        """
        if "sync_state" not in self.config:
            self.config["sync_state"] = {}
            
        self.config["sync_state"]["last_synced_id"] = tweet_id
        from datetime import datetime
        self.config["sync_state"]["last_sync_time"] = datetime.now().isoformat()
        
        self._save_config()
