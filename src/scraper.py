import time
import sys
import os
from typing import List, Set
from playwright.sync_api import Page, Locator

# Add project root to python path so we can import from src if run directly
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth import BrowserManager

class BookmarkScraper:
    """
    Scrapes bookmarks from X (Twitter).
    """
    def __init__(self, browser_manager: BrowserManager):
        self.browser = browser_manager
        self.page = browser_manager.page

    def navigate_to_bookmarks(self):
        """
        Navigates to the bookmarks page.
        """
        if not self.page:
             raise RuntimeError("Browser not initialized.")
        
        print("Navigating to Bookmarks...")
        try:
            # Relaxed waiting condition to 'domcontentloaded' to avoid timeout on heavy media loading
            self.page.goto("https://x.com/i/bookmarks", timeout=60000, wait_until="domcontentloaded")
        except Exception as e:
             print(f"⚠️ Navigation error: {e}. Retrying once...")
             time.sleep(2)
             self.page.goto("https://x.com/i/bookmarks", timeout=60000, wait_until="domcontentloaded")

        # Try waiting for 'article' OR a generic empty state message
        try:
            self.page.wait_for_selector('article', timeout=60000)
        except Exception:
             print("⚠️ Could not find 'article' elements immediately. The page might be loading or empty.")
             # We don't raise error here, let the loop handle the check
        
        print("Bookmarks page loaded (or timeout reached).")

    def scrape_bookmarks(self, limit: int = 50, max_scrolls: int = 20) -> List[Locator]:
        """
        Scrapes bookmark elements, scrolling down to load more.

        Args:
            limit (int): Approximate number of tweets to scrape.
            max_scrolls (int): Safety limit to prevent infinite loops.

        Returns:
            List[Locator]: A list of Playwright Locators representing tweet articles.
                           Note: Locators are dynamic. If the page context changes, they might become stale.
                           For processing, we might want to extract HTML content immediately.
        """
        self.navigate_to_bookmarks()
        
        collected_ids: Set[str] = set()
        tweet_locators: List[Locator] = []
        
        scroll_count = 0
        last_height = self.page.evaluate("document.body.scrollHeight")
        
        while len(tweet_locators) < limit and scroll_count < max_scrolls:
            # Find all article elements (tweets) currently in the DOM
            # We use 'article[data-testid="tweet"]' for precision
            articles = self.page.locator('article[data-testid="tweet"]').all()
            
            new_items_found = False
            for article in articles:
                # We try to find a unique identifier for the tweet to avoid duplicates.
                # Usually, the link to the tweet status contains the ID.
                # Structure: article -> ... -> a[href*="/status/"]
                try:
                    # Check if we have seen this tweet in this session
                    # Note: Extracting attributes from many elements can be slow, so we do it carefully.
                    # For a prototype, we might just collect everything and dedup later.
                    # But to stop scrolling, we need to know if we are finding NEW things.
                    
                    # This is a simplified check. In a real run, we might parse fully.
                    # Here we just count them.
                    pass
                except Exception:
                    continue

            # For the prototype, we just trust the count of unique elements in the current viewport + buffer
            # But since X virtualizes the list (removes old items from DOM as you scroll down), 
            # we cannot simply accumulate Locators. We MUST extract data or HTML immediately.
            # WAITING FOR PARSER: Since parsing is Step 4, here we will just demonstrate scrolling
            # and returning the raw HTML of the currently visible items for the user to see.
            
            print(f"Scroll {scroll_count + 1}: Found {len(articles)} visible tweets.")
            
            # Scroll down
            self.page.mouse.wheel(0, 2000) # Scroll down by pixels
            self.page.wait_for_timeout(2000) # Wait for content to load
            
            # Check if we reached bottom
            new_height = self.page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                print("Reached bottom or no new content loaded.")
                # Try one more small scroll to be sure
                self.page.mouse.wheel(0, 500)
                self.page.wait_for_timeout(2000)
                if self.page.evaluate("document.body.scrollHeight") == new_height:
                    break
            last_height = new_height
            scroll_count += 1

        # Final collection of what's currently visible
        # NOTE: To do this properly for ALL items, we need to parse-as-we-go in the loop.
        # Since this is the "Scraper Prototype" step, I will return the visible locators 
        # at the end, but add a note that in production (Step 7), we merge Scraping & Parsing.
        final_articles = self.page.locator('article[data-testid="tweet"]').all()
        return final_articles

if __name__ == "__main__":
    # Test the scraper
    manager = BrowserManager(headless=False)
    try:
        manager.start()
        if not manager.login_check():
            print("Please log in first (run auth.py).")
        else:
            scraper = BookmarkScraper(manager)
            articles = scraper.scrape_bookmarks(limit=20)
            print(f"Final visible articles: {len(articles)}")
            if len(articles) > 0:
                print("Sample Inner Text of first tweet:")
                print(articles[0].inner_text()[:100] + "...")
    finally:
        # manager.close()
        pass

