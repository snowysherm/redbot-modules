from .rconcog import RconCog


async def setup(bot):
    await bot.add_cog(RconCog(bot))
