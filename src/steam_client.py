import steam
import logging
import aiohttp
import datetime as dt

from aiohttp_socks import ProxyConnector, ProxyType, ProxyError


def resolve_proxy(proxy_string):
    host, port, login, password = proxy_string.split(':')
    return host, int(port), login, password


class SteamClient(steam.Client):

    def __init__(self, *args, database=None, proxy_info=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.proxy_info = proxy_info
        self.database = database
        self.is_connected = False

    def __eq__(self, other):
        return self.login == other.login

    async def on_connect(self):
        self.is_connected = True

        await self.database.logs.insert_one({
            "date": dt.datetime.now(),
            "type": "steam",
            "login": self.username,
            "proxy": self.proxy_info,
            "request": "login",
            "response": "Success"
        })

    async def on_disconnect(self):
        self.is_connected = False

        await self.database.logs.insert_one({
            "date": dt.datetime.now(),
            "type": "steam",
            "login": self.username,
            "proxy": self.proxy_info,
            "request": "logout",
            "response": "Success"
        })

    async def on_error(self, event: str, error: Exception, *args, **kwargs):
        await self.log_error(event, error, *args, **kwargs)

    async def on_ready(self):
        logging.info(f"{self.user.name} started!")

    async def close(self, *args, **kwargs):
        await super().close(*args, **kwargs)

    async def login(self, *args, **kwargs):
        if self.http._session is not None:
            await self.http._session.close()

        if self.proxy_info:
            try:
                host, port, login, password = resolve_proxy(self.proxy_info)
            except Exception:
                raise ProxyError("Invalid proxy")

            proxy_connector = ProxyConnector(
                proxy_type=ProxyType.SOCKS5,
                host=host,
                port=port,
                username=login,
                password=password,
                rdns=True
            )
        else:
            proxy_connector = None

        self.http._session = aiohttp.ClientSession(connector=proxy_connector)
        await super().login(*args, **kwargs)

    async def log_error(self, event, error: Exception, *args, **kwargs):
        await self.database.logs.insert_one({
            "date": dt.datetime.now(),
            "type": "steam",
            "login": self.username,
            "proxy": self.proxy_info,
            "request": event,
            "response": str(error)
        })
