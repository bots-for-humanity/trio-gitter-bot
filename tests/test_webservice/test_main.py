from aiohttp import web

from webservice import __main__ as main


async def test_root_url(aiohttp_client):
    app = web.Application()
    app.router.add_get("/", main.main)
    client = await aiohttp_client(app)
    response = await client.get("/")
    assert response.status == 200
