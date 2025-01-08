from .xcancel import xcancel


async def setup(bot):
    await bot.add_cog(xcancel(bot))
