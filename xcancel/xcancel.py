from redbot.core import commands
import re
import discord


class XCancel(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        pattern = r'https?://(?:www\.)?x\.com\S+'
        if matches := re.findall(pattern, message.content):
            xcancel_links = [x_link.replace("x.com", "xcancel.com") for x_link in matches]
            await message.reply(" ".join(xcancel_links), allowed_mentions=discord.AllowedMentions.none())


async def setup(bot):
    await bot.add_cog(XCancel(bot))
