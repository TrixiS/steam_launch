from steam_client import SteamClient


class BotsController:

    def __init__(self, *, database):
        self.database = database
        self.running_bots = []

    def is_running(self, login):
        for client in self.running_bots:
            if client.username == login:
                return client

    async def start_bot(self, bot_data):
        if self.is_running(bot_data["login"]):
            return

        client = SteamClient(
            proxy_info=bot_data.get("proxy"),
            database=self.database
        )
        self.running_bots.append(client)

        await client.start(
            bot_data.get("login"),
            bot_data.get("password"),
            shared_secret=bot_data.get("shared_secret"),
            identity_secret=bot_data.get("indentity_secret")
        )

        return client