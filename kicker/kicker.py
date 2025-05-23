from redbot.core import commands
from mcrcon import MCRcon
from dotenv import load_dotenv
import os

load_dotenv()


class Kicker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        channel = self.bot.get_channel(707383988200800358)
        if message.author == self.bot.user:
            return

        needle = "sex"

        if message.channel.id == 793150452430274601:
            if needle in message.content:
                if ":" in message.content:
                    username = message.content.split(":", 1)[0]
                    self.saved_start = username
                    print(f"Gespeicherter Anfang: {self.saved_start}")

                    try:
                        with MCRcon("192.168.178.167", os.getenv("SERVER_PASSWORD"), port=25575) as mcr:
                            response = mcr.command(f"kick {username} wir bleiben hier mal christlich")
                            await channel.send(response)
                    except Exception as e:
                        print(e)


def setup(bot):
    bot.add_cog(Kicker(bot))
