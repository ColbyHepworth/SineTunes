import json
from discord.ext.commands import Bot
from discord import Intents
from discord_slash import SlashCommand


class MusicBot(Bot):

    def __init__(self):
        super().__init__(command_prefix=None, self_bot=True, intents=Intents.default())
        self.slash = SlashCommand(self, sync_commands=True)
        self._config = None

    @property
    def config(self):
        with open("config.json") as json_file:
            return json.load(json_file)

    def run(self):
        @self.event
        async def on_ready():
            print("Ready!")
        self.load_extension("cogs.music")
        super().run(self.config["TOKEN"])

    def get_guilds(self):
        guilds = []
        for guild in self.guilds:
            guilds.append(guild)
