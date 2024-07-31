from redbot.core import commands
from discord.ext import tasks
import discord
import aiohttp
import logging


class AvailabilityChecker(commands.Cog):
    def __init__(self, bot):
        self.url = None
        self.bot = bot
        self.channel_id = None
        self.check_availability.start()
        self.found = False
        self.found_message = None
        self.not_found_message = None
        self.search_string = None

    async def send_message(self, message):
        if self.channel_id:
            channel = self.bot.get_channel(self.channel_id)
            if channel:
                await channel.send(message)

    async def check_status(self):

        if self.url is None or self.search_string is None or self.channel_id is None:
            return False

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url) as response:
                    response_text = await response.text()
                    channel = self.bot.get_channel(self.channel_id)

                    if channel is None:
                        print("Invalid channel ID.")
                        return

                    if self.search_string in response_text:
                        if not self.found:
                            await self.send_message(self.found_message)
                        self.found = True
                    else:
                        if self.found:
                            await self.send_message(self.not_found_message)
                        self.found = False
        except aiohttp.ClientError as e:
            print(f"HTTP request failed: {e}")

    @tasks.loop(hours=12)
    async def check_availability(self):
        await self.check_status()

    @commands.command()
    async def checkNow(self, ctx):
        if await self.check_status() is False:
            await ctx.send("URL, search string, or channel ID not set.")

    @check_availability.before_loop
    async def before_check_availability(self):
        await self.bot.wait_until_ready()

    @commands.command()
    async def setChannel(self, ctx, channel_id: int):
        """set channel eg. !setChannel <id>"""

        self.channel_id = channel_id
        await ctx.send(f"Notifications will be sent to <#{channel_id}>")

    @commands.command()
    async def channel(self, ctx):
        """shows current interval"""

        await ctx.send(f"<#{self.channel_id}>")

    @commands.command()
    async def setUrl(self, ctx, url: str):
        """set URL eg. !setUrl <url>"""

        self.url = url
        await ctx.send(f"URL set")

    @commands.command()
    async def url(self, ctx):
        """shows current url"""

        await ctx.send(f"{self.url}")

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
    async def interval(self, ctx):
        """shows current interval"""

        await ctx.send(f"{self.interval}")

    @commands.command()
    async def setNotFoundMessage(self, ctx, message: str):
        """message to send if search string does not match the return response"""

        self.not_found_message = message
        await ctx.send(f"Message set")

    @commands.command()
    async def notFoundMessage(self, ctx):
        """show unvailable message"""

        await ctx.send(f"{self.not_found_message}")

    @commands.command()
    async def setFoundMessage(self, ctx, message: str):
        """message to send if search string matches the return response"""
        self.found_message = message

        await ctx.send(f"Message set")

    @commands.command()
    async def foundMessage(self, ctx):
        """show unvailable message"""

        await ctx.send(f"{self.found_message}")

    @commands.command()
    async def setSearchString(self, ctx, message: str):
        """string to search for in response return"""
        self.search_string = message

        await ctx.send(f"Search string set")

    @commands.command()
    async def searchString(self, ctx):
        """show search string"""

        await ctx.send(f"{self.search_string}")

    @commands.command()
    async def acInfo(self, ctx):
        """display current bot setup"""

        embed = discord.Embed(
            title="Current AvailabilityChecker values",
            color=discord.Color.blue()
        )

        embed.add_field(name="URL", value=self.url or "Not set", inline=False)
        embed.add_field(name="Channel ID", value=self.channel_id or "Not set", inline=False)
        embed.add_field(name="Search String", value=self.search_string or "Not set", inline=False)
        embed.add_field(name="Found Message", value=self.found_message or "Not set", inline=False)
        embed.add_field(name="Not Found Message", value=self.not_found_message or "Not set", inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def acPing(self, ctx):
        log = logging.getLogger("red")
        log.info("Pong")

        await ctx.send(f"Pong")

    def cog_unload(self):
        self.check_availability.cancel()


def setup(bot):
    bot.add_cog(AvailabilityChecker(bot))
