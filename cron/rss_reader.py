from datetime import datetime

import feedparser


class RSSReader:
    def __init__(self, feed_url):
        self.feed_url = feed_url

    def read_feed(self, newer_than):
        feed = feedparser.parse(self.feed_url)

        for idx, entry in enumerate(feed.entries):
            published_ts = datetime.fromisoformat(entry["published"].replace("Z", ""))

            if idx == 0:
                if published_ts < newer_than:
                    return
            else:
                yield entry
