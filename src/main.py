import time
import sys
import os
import threading
import traceback
import random
from typing import Set, Callable, Optional, List
from datetime import datetime

# Add project root to python path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth import BrowserManager
from src.scraper import BookmarkScraper
from src.parser import TweetParser
from src.storage import StorageManager
from src.config import ConfigManager

class SyncService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SyncService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.logs: List[str] = []
        self.is_running = False
        self.is_monitoring = False
        self._stop_event = threading.Event()
        self._thread = None
        self._initialized = True

    def log(self, message: str):
        print(message)
        self.logs.append(message)
        if len(self.logs) > 500:
            self.logs.pop(0)

    def get_logs(self) -> List[str]:
        return list(self.logs)

    def start(self, monitor: bool = False):
        if self.is_running:
            self.log("⚠️ Sync already in progress.")
            return
        
        self.is_running = True
        self.is_monitoring = monitor
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_process)
        self._thread.start()

    def stop(self):
        if not self.is_running:
            return
        self.log("🛑 Stop requested...")
        self._stop_event.set()

    def _is_active_hours(self) -> bool:
        """
        Checks if current time is within active hours (e.g., 8 AM to 12 AM).
        Simulates normal human awake time.
        """
        now = datetime.now()
        # Active between 08:00 and 23:59
        return 8 <= now.hour <= 23

    def _run_process(self):
        self.log("🚀 X-Mark Sync Starting...")
        if self.is_monitoring:
            self.log("🔄 Mode: Continuous Monitoring (Human-like)")
        
        browser_mgr = None
        try:
            # 1. Load Config
            config_mgr = ConfigManager()
            obsidian_path = config_mgr.get("obsidian_vault_path")
            headless = config_mgr.get("headless_mode", False)
            max_limit = config_mgr.get("max_tweets_limit", 100)
            
            self.log(f"📁 Storage Path: {obsidian_path}")

            # 2. Initialize Modules
            browser_mgr = BrowserManager(headless=headless)
            storage_mgr = StorageManager(base_dir=obsidian_path)
            parser = TweetParser()
            
            # 3. Auth & Browser Start
            self.log("🌐 Starting Browser...")
            browser_mgr.start()
            
            if not browser_mgr.login_check():
                self.log("⚠️ Not logged in. Please log in the browser window.")
                browser_mgr.wait_for_login()
            
            # 4. Init Scraper
            scraper = BookmarkScraper(browser_mgr)
            
            # Continuous Loop
            while not self._stop_event.is_set():
                try:
                    # Check active hours if monitoring
                    if self.is_monitoring and not self._is_active_hours():
                        self.log("🌙 Outside active hours (8:00-24:00). Pausing check.")
                        # Sleep for a while (e.g., 30 mins) before re-checking time
                        for _ in range(1800): 
                            if self._stop_event.is_set(): break
                            time.sleep(1)
                        if self._stop_event.is_set(): break
                        continue

                    # Add a small random delay before starting sync cycle
                    if self.is_monitoring:
                         time.sleep(random.uniform(1, 3))
                         
                    self._perform_sync_cycle(scraper, parser, storage_mgr, config_mgr, max_limit)
                except Exception as e:
                    self.log(f"❌ Error during sync cycle: {e}")
                    traceback.print_exc()
                
                if not self.is_monitoring:
                    break
                
                if self._stop_event.is_set():
                    break

                # Random wait time between checks (e.g., 2 to 10 minutes) to simulate human checking casually
                # Widened gap to look less bot-like
                wait_time = random.randint(120, 600)
                self.log(f"💤 Waiting {wait_time} seconds before next check...")
                
                for _ in range(wait_time):
                    if self._stop_event.is_set(): break
                    time.sleep(1)
                
                if not self._stop_event.is_set():
                    self.log("🔄 Restarting check...")

        except Exception as e:
            self.log(f"❌ Critical error: {e}")
            traceback.print_exc()
        finally:
            if browser_mgr:
                browser_mgr.close()
            self.is_running = False
            self.log("✅ Service Stopped")

    def _perform_sync_cycle(self, scraper, parser, storage_mgr, config_mgr, max_limit):
        last_synced_id = config_mgr.get_last_synced_id()
        if last_synced_id:
            self.log(f"ℹ️ Last synced ID: {last_synced_id}")
        
        # Important: Refresh page to get new bookmarks
        # If we just scroll, we might be at bottom or stale state
        scraper.navigate_to_bookmarks()
        
        # Random delay after navigation
        time.sleep(random.uniform(2.0, 4.5))
        
        processed_ids: Set[str] = set()
        new_tweets_count = 0
        latest_tweet_id = None 
        
        scroll_count = 0
        max_scrolls = 50
        no_new_content_count = 0
        
        self.log("📥 Scraping bookmarks...")
        
        while len(processed_ids) < max_limit and scroll_count < max_scrolls:
            if self._stop_event.is_set(): break

            # Small chance to move mouse randomly to simulate presence
            if random.random() < 0.3:
                scraper.page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                time.sleep(random.uniform(0.2, 0.5))

            articles = scraper.page.locator('article[data-testid="tweet"]').all()
            current_batch_new = 0
            
            self.log(f"   DEBUG: Found {len(articles)} articles in viewport.")

            # Collect all tweet data first to find the latest one for sync state
            parsed_batch = []
            for article in articles:
                t_data = parser.parse_tweet(article)
                if t_data:
                    parsed_batch.append(t_data)
                else:
                    # self.log("   ⚠️ Failed to parse a tweet (might be an ad or loading).")
                    pass
            
            # If this is the first batch (top of page), the first item is potentially the newest
            if scroll_count == 0 and parsed_batch:
                potential_newest = parsed_batch[0].id
                if latest_tweet_id is None:
                    latest_tweet_id = potential_newest

            for tweet_data in parsed_batch:
                if self._stop_event.is_set(): break
                
                if tweet_data.id in processed_ids: continue
                
                # Check stop condition:
                if last_synced_id and tweet_data.id == last_synced_id:
                    self.log(f"🛑 Reached last synced tweet ({tweet_data.id}). Cycle finished.")
                    if latest_tweet_id:
                        config_mgr.update_last_synced_id(latest_tweet_id)
                    return 

                storage_mgr.save_tweet(tweet_data)
                processed_ids.add(tweet_data.id)
                new_tweets_count += 1
                current_batch_new += 1
                
                if len(processed_ids) >= max_limit:
                    break
            
            if self._stop_event.is_set(): break

            # If we found nothing new in this batch
            if current_batch_new == 0:
                no_new_content_count += 1
                if no_new_content_count >= 3:
                    self.log("⚠️ No new items found for 3 scrolls. Cycle finished.")
                    break
            else:
                no_new_content_count = 0

            # Random scroll amount
            scroll_amount = random.randint(800, 1600)
            scraper.page.mouse.wheel(0, scroll_amount)
            
            # Random sleep between scrolls
            sleep_time = random.uniform(1.5, 3.5)
            time.sleep(sleep_time)
            
            scroll_count += 1

        if new_tweets_count > 0:
            self.log(f"✅ Saved {new_tweets_count} new bookmarks this cycle.")
            if latest_tweet_id:
                config_mgr.update_last_synced_id(latest_tweet_id)
        else:
            self.log("no new bookmarks found.")

def main():
    # CLI usage remains
    service = SyncService()
    service.start(monitor=False)
    # Keep main thread alive while service runs
    try:
        while service.is_running:
            time.sleep(1)
    except KeyboardInterrupt:
        service.stop()

if __name__ == "__main__":
    main()
