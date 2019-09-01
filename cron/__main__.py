import asyncio
import os
import sys
from datetime import datetime, timedelta


from apscheduler.schedulers.asyncio import AsyncIOScheduler

import aiohttp

from .gitter_api import GitterAPI
from .rss_reader import RSSReader

sys.stdout.reconfigure(line_buffering=True)


async def rss_to_gitter_job():

    # run the script every 10 minutes
    print("Checking the RSS feed")
    ten_minutes_ago = datetime.now() - timedelta(minutes=10)
    ROOM_ID = os.getenv("GITTER_ROOM_ID")

    async with aiohttp.ClientSession() as session:
        gitter_token = os.getenv("GITTER_TOKEN")
        gitter_api = GitterAPI(session, "trio-gitter-bot", gitter_token)

        # Source: https://stackexchange.com/filters/289914/trio-project-tags-on-stackoverflow-filter
        rss_reader = RSSReader(
            "https://stackexchange.com/feeds/tagsets/289914/trio-project-tags-on-stackoverflow-filter?sort=active"
        )

        # read the RSS
        # if the post was published less than ten minutes ago, post it to gitter
        for e in rss_reader.read_feed(newer_than=ten_minutes_ago):
            await gitter_api.post(
                f"/v1/rooms/{ROOM_ID}/chatMessages",
                data={
                    "text": f"🤖❓ New `python-trio` question on stackoverflow: [{e['title']}]({e['link']})"
                },
            )


if __name__ == "__main__":
    scheduler = AsyncIOScheduler()
    scheduler.add_job(rss_to_gitter_job, "interval", minutes=10)
    scheduler.start()

    # Execution will block here until Ctrl+C (Ctrl+Break on Windows) is pressed.
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
