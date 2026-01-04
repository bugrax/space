"""
Nitter-based Twitter scraper for fetching tweets without API.

Nitter is an open-source Twitter frontend that allows scraping
without authentication or API keys.
"""

import re
import random
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from dataclasses import dataclass
import xml.etree.ElementTree as ET

import httpx
from rich.console import Console

from .models import Tweet, TweetAuthor, TweetMetrics, TweetMedia

console = Console()


# List of working Nitter instances (updated regularly)
NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org", 
    "https://nitter.1d4.us",
    "https://nitter.kavin.rocks",
    "https://nitter.unixfox.eu",
    "https://nitter.fdn.fr",
    "https://nitter.net",
]


@dataclass
class NitterConfig:
    """Configuration for Nitter scraper."""
    instances: list[str]
    timeout: int = 30
    max_retries: int = 3
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


class NitterScraper:
    """
    Scraper for fetching tweets via Nitter instances.
    
    Uses RSS feeds and HTML scraping as fallback.
    Automatically rotates between instances for reliability.
    """
    
    def __init__(self, config: Optional[NitterConfig] = None):
        """Initialize the Nitter scraper."""
        self.config = config or NitterConfig(instances=NITTER_INSTANCES)
        self.current_instance_idx = 0
        self._working_instances: list[str] = []
        
    @property
    def current_instance(self) -> str:
        """Get current Nitter instance URL."""
        if self._working_instances:
            return self._working_instances[self.current_instance_idx % len(self._working_instances)]
        return self.config.instances[self.current_instance_idx % len(self.config.instances)]
    
    def _rotate_instance(self):
        """Rotate to next instance."""
        self.current_instance_idx += 1
        
    async def _check_instance_health(self, instance: str) -> bool:
        """Check if a Nitter instance is working."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{instance}/search?q=test")
                return response.status_code == 200
        except Exception:
            return False
    
    async def find_working_instances(self) -> list[str]:
        """Find all working Nitter instances."""
        console.print("[dim]Checking Nitter instances...[/dim]")
        
        working = []
        tasks = [self._check_instance_health(inst) for inst in self.config.instances]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for inst, result in zip(self.config.instances, results):
            if result is True:
                working.append(inst)
                console.print(f"  [green]✓[/green] {inst}")
            else:
                console.print(f"  [red]✗[/red] {inst}")
        
        self._working_instances = working
        return working
    
    async def _fetch_with_retry(self, url: str) -> Optional[str]:
        """Fetch URL with retry logic and instance rotation."""
        for attempt in range(self.config.max_retries):
            instance = self.current_instance
            full_url = f"{instance}{url}"
            
            try:
                async with httpx.AsyncClient(
                    timeout=self.config.timeout,
                    headers={"User-Agent": self.config.user_agent},
                    follow_redirects=True
                ) as client:
                    response = await client.get(full_url)
                    
                    if response.status_code == 200:
                        return response.text
                    elif response.status_code == 429:
                        # Rate limited, try another instance
                        console.print(f"[yellow]Rate limited on {instance}, rotating...[/yellow]")
                        self._rotate_instance()
                    else:
                        console.print(f"[yellow]Got {response.status_code} from {instance}[/yellow]")
                        self._rotate_instance()
                        
            except Exception as e:
                console.print(f"[red]Error with {instance}: {e}[/red]")
                self._rotate_instance()
                
            await asyncio.sleep(1)  # Brief delay between retries
        
        return None
    
    def _parse_rss_feed(self, xml_content: str) -> list[Tweet]:
        """Parse Nitter RSS feed into Tweet objects."""
        tweets = []
        
        try:
            root = ET.fromstring(xml_content)
            channel = root.find("channel")
            
            if channel is None:
                return tweets
            
            for item in channel.findall("item"):
                tweet = self._parse_rss_item(item)
                if tweet:
                    tweets.append(tweet)
                    
        except ET.ParseError as e:
            console.print(f"[red]RSS parse error: {e}[/red]")
            
        return tweets
    
    def _parse_rss_item(self, item: ET.Element) -> Optional[Tweet]:
        """Parse a single RSS item into a Tweet."""
        try:
            # Extract basic fields
            title = item.find("title")
            link = item.find("link")
            pub_date = item.find("pubDate")
            description = item.find("description")
            creator = item.find("{http://purl.org/dc/elements/1.1/}creator")
            
            if title is None or link is None:
                return None
            
            # Extract tweet ID from link
            link_text = link.text or ""
            tweet_id_match = re.search(r'/status/(\d+)', link_text)
            tweet_id = tweet_id_match.group(1) if tweet_id_match else str(hash(link_text))
            
            # Extract username
            username = ""
            if creator is not None and creator.text:
                username = creator.text.replace("@", "")
            else:
                # Try to extract from link
                username_match = re.search(r'nitter\.[^/]+/([^/]+)/', link_text)
                if username_match:
                    username = username_match.group(1)
            
            # Get tweet text
            text = ""
            if description is not None and description.text:
                # Clean HTML from description
                text = re.sub(r'<[^>]+>', '', description.text)
                text = text.strip()
            elif title is not None and title.text:
                text = title.text
            
            # Parse date
            created_at = datetime.now(timezone.utc)
            if pub_date is not None and pub_date.text:
                try:
                    # Format: "Sat, 04 Jan 2026 12:30:00 GMT"
                    created_at = datetime.strptime(
                        pub_date.text, 
                        "%a, %d %b %Y %H:%M:%S %Z"
                    ).replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
            
            # Extract URLs from text
            urls = re.findall(r'https?://[^\s<>"]+', text)
            
            # Extract hashtags
            hashtags = re.findall(r'#(\w+)', text)
            
            # Extract media (images in description)
            media = []
            if description is not None and description.text:
                img_urls = re.findall(r'<img[^>]+src="([^"]+)"', description.text)
                for img_url in img_urls:
                    media.append(TweetMedia(
                        media_key=f"img_{hash(img_url)}",
                        type="photo",
                        url=img_url
                    ))
            
            return Tweet(
                id=tweet_id,
                text=text,
                created_at=created_at,
                author=TweetAuthor(
                    id=f"user_{hash(username)}",
                    username=username,
                    name=username,  # RSS doesn't provide display name
                    followers_count=0,  # Not available in RSS
                    verified=False
                ),
                metrics=TweetMetrics(
                    like_count=0,  # Not available in RSS
                    retweet_count=0,
                    reply_count=0,
                    impression_count=0
                ),
                media=media,
                urls=urls,
                hashtags=hashtags
            )
            
        except Exception as e:
            console.print(f"[red]Error parsing RSS item: {e}[/red]")
            return None
    
    def _parse_html_tweets(self, html_content: str) -> list[Tweet]:
        """Parse tweets from Nitter HTML page."""
        tweets = []
        
        # Find all tweet containers
        tweet_pattern = re.compile(
            r'<div class="timeline-item[^"]*"[^>]*>.*?</div>\s*</div>\s*</div>',
            re.DOTALL
        )
        
        for match in tweet_pattern.finditer(html_content):
            tweet_html = match.group(0)
            tweet = self._parse_html_tweet(tweet_html)
            if tweet:
                tweets.append(tweet)
        
        return tweets
    
    def _parse_html_tweet(self, html: str) -> Optional[Tweet]:
        """Parse a single tweet from HTML."""
        try:
            # Extract tweet ID
            id_match = re.search(r'/status/(\d+)', html)
            tweet_id = id_match.group(1) if id_match else None
            if not tweet_id:
                return None
            
            # Extract username
            username_match = re.search(r'class="username"[^>]*>@?([^<]+)</a>', html)
            username = username_match.group(1) if username_match else "unknown"
            
            # Extract display name
            name_match = re.search(r'class="fullname"[^>]*>([^<]+)</a>', html)
            name = name_match.group(1) if name_match else username
            
            # Extract tweet text
            text_match = re.search(r'class="tweet-content[^"]*"[^>]*>([^<]+(?:<[^>]+>[^<]*)*)</div>', html)
            text = ""
            if text_match:
                text = re.sub(r'<[^>]+>', ' ', text_match.group(1))
                text = ' '.join(text.split())  # Normalize whitespace
            
            # Extract stats
            likes = self._extract_stat(html, 'icon-heart') or 0
            retweets = self._extract_stat(html, 'icon-retweet') or 0
            replies = self._extract_stat(html, 'icon-comment') or 0
            
            # Extract date
            date_match = re.search(r'<span class="tweet-date"[^>]*><a[^>]+title="([^"]+)"', html)
            created_at = datetime.now(timezone.utc)
            if date_match:
                try:
                    # Format varies, try common patterns
                    date_str = date_match.group(1)
                    for fmt in ["%b %d, %Y · %I:%M %p %Z", "%Y-%m-%d %H:%M:%S"]:
                        try:
                            created_at = datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass
            
            # Extract URLs
            urls = re.findall(r'href="(https?://[^"]+)"', html)
            urls = [u for u in urls if 'nitter' not in u and 'twitter' not in u]
            
            # Extract hashtags
            hashtags = re.findall(r'href="/search\?q=%23(\w+)"', html)
            
            # Extract images
            media = []
            img_matches = re.findall(r'class="still-image"[^>]+href="([^"]+)"', html)
            for img_url in img_matches:
                media.append(TweetMedia(
                    media_key=f"img_{hash(img_url)}",
                    type="photo",
                    url=img_url
                ))
            
            return Tweet(
                id=tweet_id,
                text=text,
                created_at=created_at,
                author=TweetAuthor(
                    id=f"user_{hash(username)}",
                    username=username,
                    name=name,
                    followers_count=0,
                    verified=False
                ),
                metrics=TweetMetrics(
                    like_count=likes,
                    retweet_count=retweets,
                    reply_count=replies,
                    impression_count=0
                ),
                media=media,
                urls=urls,
                hashtags=hashtags
            )
            
        except Exception as e:
            console.print(f"[red]Error parsing HTML tweet: {e}[/red]")
            return None
    
    def _extract_stat(self, html: str, icon_class: str) -> int:
        """Extract a stat value from tweet HTML."""
        pattern = rf'{icon_class}[^>]*></span>\s*<span[^>]*>([^<]+)</span>'
        match = re.search(pattern, html)
        if match:
            stat_str = match.group(1).strip().replace(',', '')
            # Handle K/M suffixes
            if 'K' in stat_str.upper():
                return int(float(stat_str.upper().replace('K', '')) * 1000)
            if 'M' in stat_str.upper():
                return int(float(stat_str.upper().replace('M', '')) * 1000000)
            try:
                return int(stat_str)
            except ValueError:
                return 0
        return 0
    
    async def search_tweets(
        self,
        query: str,
        max_results: int = 100
    ) -> list[Tweet]:
        """
        Search for tweets matching a query.
        
        Args:
            query: Search query (keywords, hashtags, etc.)
            max_results: Maximum number of tweets to return
        
        Returns:
            List of Tweet objects
        """
        # URL encode the query
        encoded_query = query.replace(' ', '+').replace('#', '%23')
        
        # Try RSS feed first (more reliable parsing)
        rss_url = f"/search/rss?f=tweets&q={encoded_query}"
        rss_content = await self._fetch_with_retry(rss_url)
        
        if rss_content:
            tweets = self._parse_rss_feed(rss_content)
            if tweets:
                console.print(f"[green]Found {len(tweets)} tweets via RSS[/green]")
                return tweets[:max_results]
        
        # Fallback to HTML scraping
        html_url = f"/search?f=tweets&q={encoded_query}"
        html_content = await self._fetch_with_retry(html_url)
        
        if html_content:
            tweets = self._parse_html_tweets(html_content)
            console.print(f"[green]Found {len(tweets)} tweets via HTML[/green]")
            return tweets[:max_results]
        
        console.print("[red]No tweets found[/red]")
        return []
    
    async def search_by_hashtags(
        self,
        hashtags: list[str],
        max_results: int = 100
    ) -> list[Tweet]:
        """
        Search for tweets with specific hashtags.
        
        Args:
            hashtags: List of hashtags (without #)
            max_results: Maximum number of tweets to return
        
        Returns:
            List of Tweet objects
        """
        # Build query with OR for multiple hashtags
        query = " OR ".join(f"#{tag}" for tag in hashtags)
        return await self.search_tweets(query, max_results)
    
    async def search_revenue_tweets(
        self,
        hashtags: Optional[list[str]] = None,
        max_results: int = 100
    ) -> list[Tweet]:
        """
        Search for tweets mentioning revenue/MRR.
        
        Args:
            hashtags: Optional hashtag filter
            max_results: Maximum tweets to return
        
        Returns:
            List of Tweet objects with revenue mentions
        """
        # Revenue-related query parts
        revenue_terms = ["MRR", "ARR", "revenue", "$", "per month", "paying customers"]
        
        queries = []
        
        # If hashtags provided, search within those
        if hashtags:
            for tag in hashtags:
                for term in ["MRR", "ARR", "revenue"]:
                    queries.append(f"#{tag} {term}")
        else:
            # Default hashtags for indie hackers
            default_tags = ["buildinpublic", "indiehackers", "saas", "microsaas"]
            for tag in default_tags:
                queries.append(f"#{tag} MRR")
                queries.append(f"#{tag} revenue")
        
        all_tweets = []
        seen_ids = set()
        
        for query in queries[:5]:  # Limit queries to avoid rate limits
            tweets = await self.search_tweets(query, max_results=30)
            for tweet in tweets:
                if tweet.id not in seen_ids:
                    seen_ids.add(tweet.id)
                    all_tweets.append(tweet)
            
            await asyncio.sleep(1)  # Brief delay between queries
        
        # Sort by engagement (likes + retweets)
        all_tweets.sort(
            key=lambda t: t.metrics.like_count + t.metrics.retweet_count,
            reverse=True
        )
        
        return all_tweets[:max_results]
    
    async def get_user_tweets(
        self,
        username: str,
        max_results: int = 50
    ) -> list[Tweet]:
        """
        Get tweets from a specific user.
        
        Args:
            username: Twitter username (without @)
            max_results: Maximum tweets to return
        
        Returns:
            List of Tweet objects
        """
        # Try RSS feed first
        rss_url = f"/{username}/rss"
        rss_content = await self._fetch_with_retry(rss_url)
        
        if rss_content:
            tweets = self._parse_rss_feed(rss_content)
            if tweets:
                return tweets[:max_results]
        
        # Fallback to HTML
        html_url = f"/{username}"
        html_content = await self._fetch_with_retry(html_url)
        
        if html_content:
            return self._parse_html_tweets(html_content)[:max_results]
        
        return []


class NitterClient:
    """
    Synchronous wrapper around NitterScraper for compatibility
    with existing TwitterClient interface.
    """
    
    def __init__(self, bearer_token: Optional[str] = None):
        """Initialize the Nitter client."""
        self.scraper = NitterScraper()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create event loop."""
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            return self._loop
    
    def _run_async(self, coro):
        """Run async function synchronously."""
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, create a task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        except RuntimeError:
            # No running loop, we can use asyncio.run
            return asyncio.run(coro)
    
    def search_tweets(
        self,
        query: str,
        max_results: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> list[Tweet]:
        """Search for tweets matching a query."""
        return self._run_async(
            self.scraper.search_tweets(query, max_results)
        )
    
    def search_by_hashtags(
        self,
        hashtags: list[str],
        max_results: int = 100,
        days: int = 7
    ) -> list[Tweet]:
        """Search for tweets with specific hashtags."""
        return self._run_async(
            self.scraper.search_by_hashtags(hashtags, max_results)
        )
    
    def search_by_keywords(
        self,
        keywords: list[str],
        max_results: int = 100,
        days: int = 7
    ) -> list[Tweet]:
        """Search for tweets containing keywords."""
        query = " OR ".join(keywords)
        return self._run_async(
            self.scraper.search_tweets(query, max_results)
        )
    
    def search_revenue_tweets(
        self,
        hashtags: Optional[list[str]] = None,
        min_mrr_mention: bool = True,
        require_image: bool = False,
        max_results: int = 100,
        days: int = 7
    ) -> list[Tweet]:
        """Search for tweets mentioning revenue/MRR."""
        return self._run_async(
            self.scraper.search_revenue_tweets(hashtags, max_results)
        )
    
    def get_user_tweets(
        self,
        username: str,
        max_results: int = 50
    ) -> list[Tweet]:
        """Get tweets from a specific user."""
        return self._run_async(
            self.scraper.get_user_tweets(username, max_results)
        )


def get_nitter_client() -> NitterClient:
    """Get a Nitter client instance."""
    return NitterClient()
