import uvicorn
import asyncio


class Server(uvicorn.Server):

    def run(self, *args, loop=None, **kwargs):
        self.config.setup_event_loop()
        loop = loop or asyncio.get_event_loop()
        loop.run_until_complete(self.serve(*args, **kwargs))
