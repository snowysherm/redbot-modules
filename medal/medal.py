from redbot.core import commands
import discord


class Medal(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.target_user_id = 307998818547531777
        self.target_channel_id = 1349869798103842866
        self.banned_url = "https://medal.tv/?utm_source=discord&utm_content=share_message"

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == self.target_user_id and message.channel.id == self.target_channel_id:
            if self.banned_url in message.content:
                try:
                    await message.delete()
                except discord.Forbidden:
                    print("Fehlende Berechtigungen zum Löschen von Nachrichten")
                except discord.NotFound:
                    print("Nachricht wurde bereits gelöscht")


async def setup(bot):
    await bot.add_cog(Medal(bot))
