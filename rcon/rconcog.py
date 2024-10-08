from redbot.core import commands
from mcrcon import MCRcon
from dotenv import load_dotenv
import os

load_dotenv()


class RconCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def whitelistadd(self, ctx, username: str):
        await ctx.typing()
        try:
            with MCRcon("192.168.178.167", os.getenv("SERVER_PASSWORD"), port=25575) as mcr:
                response = mcr.command(f"whitelist add {username}")
                if response == f"Added {username} to the whitelist":
                    await ctx.message.add_reaction("✅")
                else:
                    await ctx.message.add_reaction("❌")
        except Exception as e:
            await ctx.message.add_reaction("❌")
            print(e)


def setup(bot):
    bot.add_cog(RconCog(bot))
