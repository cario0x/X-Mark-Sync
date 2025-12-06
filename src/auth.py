import os
from playwright.sync_api import sync_playwright, BrowserContext, Page
from typing import Optional

class BrowserManager:
    """
    Manages the Playwright browser instance and persistent context.
    """
    def __init__(self, headless: bool = False, user_data_dir: str = "data/browser_context"):
        """
        Initialize the BrowserManager.

        Args:
            headless (bool): Whether to run the browser in headless mode. Defaults to False for debugging/login.
            user_data_dir (str): Path to store the persistent browser context (cookies, local storage).
        """
        self.headless = headless
        self.user_data_dir = os.path.abspath(user_data_dir)
        self.playwright = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def start(self):
        """
        Starts the Playwright engine and launches a persistent context.
        """
        if not os.path.exists(self.user_data_dir):
            os.makedirs(self.user_data_dir)

        self.playwright = sync_playwright().start()
        
        # Launch persistent context. This saves login state to user_data_dir.
        # viewport=None allows the window to be resized freely.
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            viewport=None, 
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled", # Hide automation status
                "--no-sandbox", # Required in some environments
                "--disable-setuid-sandbox"
            ],
            ignore_default_args=["--enable-automation"] # Hide "Chrome is controlled by automated software" bar
        )
        
        # Get the first page or create a new one
        if len(self.context.pages) > 0:
            self.page = self.context.pages[0]
        else:
            self.page = self.context.new_page()
            
        print(f"Browser started with context at: {self.user_data_dir}")

    def close(self):
        """
        Closes the browser context and stops Playwright.
        """
        if self.context:
            self.context.close()
        if self.playwright:
            self.playwright.stop()
        print("Browser closed.")

    def login_check(self, url: str = "https://x.com/home") -> bool:
        """
        Checks if the user is logged in by navigating to the home page.
        If redirected to login, returns False.
        
        Args:
            url (str): URL to check. Defaults to X home page.
            
        Returns:
            bool: True if logged in, False otherwise.
        """
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")

        print(f"Navigating to {url} to check login status...")
        try:
            self.page.goto(url, timeout=60000)
            # 'networkidle' can be flaky on X/Twitter because of constant background streams.
            # 'domcontentloaded' is safer for initial check.
            self.page.wait_for_load_state("domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"⚠️ Navigation warning: {e}")
            # Continue anyway to check URL/content

        # Simple check: If the URL contains 'login' or 'logout', we are likely not logged in.
        # A better check might be looking for a specific element that only exists when logged in,
        # e.g., the "Post" button or user profile icon.
        # For X, if not logged in, it usually redirects to x.com/i/flow/login or just x.com
        # But if we go to /home and stay there, we are good.
        
        current_url = self.page.url
        if "login" in current_url or current_url == "https://x.com/":
             # Further check: look for a specific element, e.g., the "Home" nav item
             try:
                 # Using a generic selector that usually appears for logged-in users
                 # aria-label="Home" is a good candidate for X
                 self.page.wait_for_selector('[aria-label="Home"]', timeout=5000)
                 return True
             except:
                 return False
        
        return True

    def wait_for_login(self):
        """
        Keeps the browser open and waits for the user to manually login.
        Useful for the initial setup.
        """
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
            
        print("Please log in to X (Twitter) in the opened browser window.")
        print("Waiting for you to reach the Home page...")
        
        try:
            # Wait until the "Home" element is visible, indicating successful login
            self.page.wait_for_selector('[aria-label="Home"]', timeout=0) # timeout=0 means wait indefinitely
            print("Login detected! You can now close this script or proceed.")
        except KeyboardInterrupt:
            print("Login wait interrupted by user.")

if __name__ == "__main__":
    # Test the module
    manager = BrowserManager(headless=False)
    try:
        manager.start()
        if manager.login_check():
            print("✅ Already logged in!")
        else:
            print("❌ Not logged in.")
            manager.wait_for_login()
    finally:
        # Keep open for a moment to see result if needed, or close immediately
        # manager.close() 
        pass

