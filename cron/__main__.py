import asyncio
import os
from datetime import datetime, timedelta

import aiohttp

from .gitter_api import GitterAPI
from .rss_reader import RSSReader


async def main():

    # run the script every 10 minutes

    ten_minutes_ago = datetime.now() - timedelta(minutes=10)
    ROOM_ID = os.getenv("GITTER_ROOM_ID")

    async with aiohttp.ClientSession() as session:
        gitter_token = os.getenv("GITTER_TOKEN")
        gitter_api = GitterAPI(session, "trio-gitter-bot", gitter_token)

        rss_reader = RSSReader("https://stackoverflow.com/feeds/tag?tagnames=python-trio&sort=newest")

        # read the RSS
        # if the post was published less than ten minutes ago, post it to gitter

        for e in rss_reader.read_feed(newer_than=ten_minutes_ago):
            await gitter_api.post(f"/v1/rooms/{ROOM_ID}/chatMessages", data={"text":
f"""
🤖❓ New `python-trio` question in stackoverflow:
**Title**: {e['title']}
**Posted by**: [{e['author_detail']['name']}]({e['author_detail']['href']})
**Time**: {e['published']}
**Summary**: {e['summary_detail']['value'][:200]}...

**Read the rest at:** {e['link']}
"""}
            )


asyncio.run(main())
