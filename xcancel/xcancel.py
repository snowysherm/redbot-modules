from redbot.core import commands
import re


class XCancel(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        pattern = r'https?://(?:www\.)?x\.com\S+'
        if matches := re.findall(pattern, message.content):
            for x_link in matches:
                xcancel_link = x_link.replace("x.com", "xcancel.com")
                await message.reply(xcancel_link)


async def setup(bot):
    await bot.add_cog(XCancel(bot))
