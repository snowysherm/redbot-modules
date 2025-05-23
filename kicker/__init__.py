from .kicker import Kicker


async def setup(bot):
    await bot.add_cog(Kicker(bot))
