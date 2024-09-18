from redbot.core import commands
import discord
from discord.ext import commands
from mcrcon import MCRcon

class rcon(commands.Cog):
    def __init__(self, bot):
        self.server_ip = None

    @commands.command()
    async def setIp(self, ctx, ip):
        self.server_ip = ip

    @commands.command()
    async def whitelist(message, minecraft_username: str):
        try:
            with MCRcon("", "rcon_passwort", port=25575) as mcr:
                response = mcr.command(f"whitelist add {minecraft_username}")
                await message.add_reaction("👍")
                print(response)
        except Exception as e:
            print(e)


def setup(bot):
    bot.add_cog(rcon(bot))
