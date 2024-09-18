from .rcon import rcon


async def setup(bot):
    await bot.add_cog(rcon(bot))
