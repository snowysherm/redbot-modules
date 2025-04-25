from .greetingwatcher import GreetingWatcher


async def setup(bot):
    await bot.add_cog(GreetingWatcher(bot))
