from redbot.core import commands
from discord.ext import tasks
import aiohttp


class AvailabilityChecker(commands.Cog):
    def __init__(self, bot):
        self.url = None
        self.bot = bot
        self.channel_id = None
        self.check_availability.start()
        self.found = False
        self.found_message = "found"
        self.not_found_message = "not found"
        self.search_string = None

    @tasks.loop(seconds=10)
    async def check_availability(self):
        async with aiohttp.ClientSession() as session:
            if self.url is not None:
                async with session.get(self.url) as response:
                    response_text = await response.text()
                    if self.search_string is not None:
                        if self.search_string in response_text:
                            if not self.found:
                                await self.send_message(self.found_message)

                            self.found = True
                        else:
                            if self.found:
                                await self.send_message(self.not_found_message)
                            self.found = False

    async def send_message(self, message):
        if self.channel_id:
            channel = self.bot.get_channel(self.channel_id)
            if channel:
                await channel.send(message)

    @check_availability.before_loop
    async def before_check_availability(self):
        await self.bot.wait_until_ready()

    @commands.command()
    async def setChannel(self, ctx, channel_id: int):
        """set channel eg. !setChannel <id>"""
        self.channel_id = channel_id
        await ctx.send(f"Notifications will be sent to <#{channel_id}>")

    @commands.command()
    async def setUrl(self, ctx, url: str):
        """set URL eg. !setUrl <url>"""
        self.url = url
        await ctx.send(f"URL set")

    @commands.command()
    async def setInterval(self, ctx, interval: int, unit: str):
        """set Interval eg. !setInterval <interval> <unit>"""
        if unit == "seconds":
            self.check_availability.change_interval(seconds=interval)
        elif unit == "minutes":
            self.check_availability.change_interval(minutes=interval)
        elif unit == "hours":
            self.check_availability.change_interval(hours=interval)
        else:
            ctx.send("error")

        await ctx.send(f"Message will be sent every {interval} {unit}")

    @commands.command()
    async def setAvailableMessage(self, ctx, message: str):
        """message to send if search string matches return response"""
        self.found_message = message

        await ctx.send(f"Message set")

    @commands.command()
    async def setUnavailableMessage(self, ctx, message: str):
        """message to send if search string does not match return response"""
        self.not_found_message = message

        await ctx.send(f"Message set")

    @commands.command()
    async def setSearchString(self, ctx, message: str):
        """string to search for in response return"""
        self.search_string = message

        await ctx.send(f"Search string set")

    def cog_unload(self):
        self.check_availability.cancel()


def setup(bot):
    bot.add_cog(AvailabilityChecker(bot))
