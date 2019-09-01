from datetime import datetime, timedelta

import feedparser


class RSSReader:
    def __init__(self, feed_url):
        self.feed_url = feed_url

    def read_feed(self, newer_than):
        feed = feedparser.parse(self.feed_url)

        print(len(feed.entries))

        for idx, entry in enumerate(feed.entries):
            published_ts = datetime.strptime(entry["published"], "%Y-%m-%dT%H:%M:%SZ")

            if published_ts < newer_than:
                return

            yield entry
