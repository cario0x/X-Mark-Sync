from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from playwright.sync_api import Locator
import time

@dataclass
class TweetData:
    """
    Data structure for a single tweet.
    """
    id: str
    url: str
    author_name: str
    author_handle: str
    date: str # ISO format string
    content: str
    media_urls: List[str] = field(default_factory=list)
    is_thread: bool = False
    avatar_url: Optional[str] = None
    reply_count: str = "0"
    retweet_count: str = "0"
    like_count: str = "0"

class TweetParser:
    """
    Parses a Tweet Locator to extract structured data.
    """

    def parse_tweet(self, tweet_locator: Locator) -> Optional[TweetData]:
        """
        Extracts data from a tweet element.
        """
        try:
            # 0. Expand "Show more" if present (for long articles/tweets)
            try:
                show_more_btn = tweet_locator.get_by_text("Show more")
                if show_more_btn.count() > 0 and show_more_btn.is_visible():
                    show_more_btn.click(timeout=1000)
                    time.sleep(0.5) # Wait for expansion
            except Exception:
                pass

            # 1. Extract Tweet URL and ID
            # Priority 1: Time element (standard tweets)
            time_locator = tweet_locator.locator("time")
            if time_locator.count() > 0:
                link_locator = time_locator.locator("..") 
                url_suffix = link_locator.get_attribute("href")
                if url_suffix:
                    tweet_url = f"https://x.com{url_suffix}"
                    tweet_id = url_suffix.split("/")[-1]
                    date_str = time_locator.get_attribute("datetime")
                else:
                    return None
            else:
                # Priority 2: Fallback for tweets where time might be hidden or structured differently (e.g. Ads or specific layouts)
                # Try finding any link that looks like a status link
                # This is a heuristic fallback
                status_link = tweet_locator.locator('a[href*="/status/"]').first
                if status_link.count() > 0:
                    url_suffix = status_link.get_attribute("href")
                    if url_suffix:
                        tweet_url = f"https://x.com{url_suffix}"
                        tweet_id = url_suffix.split("/")[-1]
                        date_str = datetime.now().isoformat() # Approximate
                    else:
                        return None
                else:
                    return None

            # 2. Extract Author Info & Avatar
            user_info_locator = tweet_locator.locator('[data-testid="User-Name"]')
            if user_info_locator.count() > 0:
                user_text = user_info_locator.inner_text()
                parts = user_text.split("\n")
                if len(parts) >= 2:
                    author_name = parts[0]
                    author_handle = parts[1]
                else:
                    author_name = parts[0] if parts else "Unknown"
                    author_handle = "@unknown"
            else:
                 author_name = "Unknown"
                 author_handle = "@unknown"

            # Avatar
            avatar_url = None
            avatar_img = tweet_locator.locator('[data-testid="Tweet-User-Avatar"] img')
            if avatar_img.count() > 0:
                avatar_url = avatar_img.first.get_attribute("src")

            # 3. Extract Content
            text_locator = tweet_locator.locator('[data-testid="tweetText"]')
            content = text_locator.inner_text() if text_locator.count() > 0 else ""

            # 4. Extract Media
            media_urls = []
            
            # Images
            photos = tweet_locator.locator('[data-testid="tweetPhoto"] img').all()
            for photo in photos:
                src = photo.get_attribute("src")
                if src:
                    media_urls.append(src)
            
            # Videos
            videos = tweet_locator.locator('[data-testid="videoPlayer"] video').all()
            for video in videos:
                # Try src
                src = video.get_attribute("src")
                if src and not src.startswith("blob:"):
                    media_urls.append(src)
                else:
                    # Try poster
                    poster = video.get_attribute("poster")
                    if poster:
                        media_urls.append(poster)
                        
            media_urls = list(dict.fromkeys(media_urls))

            # 5. Stats (Likes, RTs)
            def get_stat(testid):
                el = tweet_locator.locator(f'[data-testid="{testid}"]').first
                if el.count() > 0:
                    val = el.get_attribute("aria-label")
                    if not val:
                        val = el.inner_text()
                    return val.split(" ")[0] if val else "0"
                return "0"

            reply_count = get_stat("reply")
            retweet_count = get_stat("retweet")
            like_count = get_stat("like")

            return TweetData(
                id=tweet_id,
                url=tweet_url,
                author_name=author_name,
                author_handle=author_handle,
                date=date_str or datetime.now().isoformat(),
                content=content,
                media_urls=media_urls,
                avatar_url=avatar_url,
                reply_count=reply_count,
                retweet_count=retweet_count,
                like_count=like_count
            )

        except Exception as e:
            # print(f"Parser Error: {e}")
            return None
