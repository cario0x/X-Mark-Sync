import os
import yaml
import requests
from datetime import datetime
from dateutil import parser as date_parser
from urllib.parse import urlparse
from src.parser import TweetData

class StorageManager:
    """
    Handles saving TweetData to Markdown files.
    """
    def __init__(self, base_dir: str = "data/bookmarks"):
        self.base_dir = os.path.abspath(base_dir)
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
            
        # Create attachments directory
        self.attachments_dir = os.path.join(self.base_dir, "attachments")
        if not os.path.exists(self.attachments_dir):
            os.makedirs(self.attachments_dir)

    def _sanitize_filename(self, text: str) -> str:
        return "".join([c for c in text if c.isalpha() or c.isdigit() or c in (' ', '-', '_', '.')]).strip()

    def _get_file_path(self, tweet: TweetData) -> str:
        try:
            dt = date_parser.parse(tweet.date)
        except:
            dt = datetime.now()

        year = str(dt.year)
        month = f"{dt.month:02d}"
        
        dir_path = os.path.join(self.base_dir, year, month)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        filename = f"{dt.strftime('%Y-%m-%d')}-{tweet.id}.md"
        return os.path.join(dir_path, filename)

    def _download_media(self, url: str, tweet_id: str, is_avatar: bool = False) -> str:
        """
        Downloads media and returns relative path for Obsidian.
        """
        try:
            parsed_url = urlparse(url)
            path = parsed_url.path
            ext = os.path.splitext(path)[1]
            if not ext:
                ext = ".jpg"
            if '?' in ext:
                ext = ext.split('?')[0]

            prefix = "avatar_" if is_avatar else "media_"
            original_name = os.path.basename(path)
            if not original_name:
                original_name = f"{prefix}{tweet_id}{ext}"
            
            safe_name = self._sanitize_filename(original_name)
            final_name = f"{tweet_id}_{prefix}{safe_name}"
            
            save_path = os.path.join(self.attachments_dir, final_name)
            
            if not os.path.exists(save_path):
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                response = requests.get(url, headers=headers, stream=True, timeout=10)
                if response.status_code == 200:
                    with open(save_path, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                else:
                    return url
            
            return f"../../attachments/{final_name}"

        except Exception as e:
            print(f"⚠️ Error downloading media {url}: {e}")
            return url

    def save_tweet(self, tweet: TweetData) -> str:
        file_path = self._get_file_path(tweet)
        
        if os.path.exists(file_path):
            return file_path

        # Download Avatar
        local_avatar = ""
        if tweet.avatar_url:
            local_avatar = self._download_media(tweet.avatar_url, tweet.id, is_avatar=True)

        # Download Media
        local_media_links = []
        if tweet.media_urls:
            for url in tweet.media_urls:
                local_link = self._download_media(url, tweet.id)
                local_media_links.append(local_link)

        # Prepare Frontmatter
        frontmatter = {
            "id": tweet.id,
            "url": tweet.url,
            "author": tweet.author_handle,
            "author_name": tweet.author_name,
            "date": tweet.date,
            "tags": ["twitter", "bookmark"],
            "created_at": datetime.now().isoformat()
        }

        # Format Content with HTML for "1:1" look
        # Using Obsidian Callouts and custom HTML for layout
        
        md_content = "---\n"
        md_content += yaml.dump(frontmatter, allow_unicode=True, sort_keys=False)
        md_content += "---\n\n"

        # Tweet Header (Avatar + Name)
        md_content += f"> [!info]+ Tweet\n"
        md_content += f"> <div style='display: flex; align-items: center; gap: 10px;'>\n"
        if local_avatar:
             # Obsidian Image syntax inside HTML needs to be standard MD or HTML img
             # Using HTML img with relative path might be tricky if relative to MD file
             # standard markdown image: ![]()
             # let's use a hack: standard md image inside div? Obsidian supports it.
             md_content += f">   <img src='{local_avatar}' style='width: 48px; height: 48px; border-radius: 50%;' />\n"
        else:
             md_content += f">   <div style='width: 48px; height: 48px; background: #ccc; border-radius: 50%;'></div>\n"
             
        md_content += f">   <div>\n"
        md_content += f">     <b style='font-size: 16px;'>{tweet.author_name}</b> <br/>\n"
        md_content += f">     <span style='color: #666;'>{tweet.author_handle} · {tweet.date[:10]}</span>\n"
        md_content += f">   </div>\n"
        md_content += f"> </div>\n>\n"
        
        # Tweet Content
        # Replace newlines with <br/> or blockquote break
        formatted_content = tweet.content.replace("\n", "\n> ")
        md_content += f"> {formatted_content}\n>\n"
        
        # Media Grid
        if local_media_links:
            md_content += f"> <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-top: 10px;'>\n"
            for link in local_media_links:
                # Standard MD image syntax works inside blockquotes in Obsidian, but inside HTML div...
                # Obsidian usually renders MD inside HTML if it's simple.
                # Safest is to use HTML img tag
                md_content += f">   <img src='{link}' style='width: 100%; border-radius: 10px;' />\n"
            md_content += f"> </div>\n>\n"
            
        # Footer Stats
        md_content += f"> <hr style='margin: 10px 0; border: 0; border-top: 1px solid #eee;' />\n"
        md_content += f"> <div style='display: flex; justify-content: space-between; color: #666; font-size: 14px;'>\n"
        md_content += f">   <span>💬 {tweet.reply_count}</span>\n"
        md_content += f">   <span>🔁 {tweet.retweet_count}</span>\n"
        md_content += f">   <span>❤️ {tweet.like_count}</span>\n"
        md_content += f">   <span><a href='{tweet.url}'>🔗 Original</a></span>\n"
        md_content += f"> </div>\n"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        return file_path
