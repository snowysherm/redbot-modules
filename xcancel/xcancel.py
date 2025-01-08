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
            reply_message = " ".join(xcancel_links)
            if len(reply_message) > 2000:
                await message.reply("<:warndreieck:1304388231835422780>", allowed_mentions=discord.AllowedMentions.none())
                return
            await message.reply(reply_message, allowed_mentions=discord.AllowedMentions.none())
            await message.edit(suppress=True)


async def setup(bot):
    await bot.add_cog(XCancel(bot))
