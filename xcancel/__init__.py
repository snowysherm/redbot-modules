from .xcancel import XCancel


async def setup(bot):
    await bot.add_cog(XCancel(bot))
