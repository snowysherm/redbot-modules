from .medal import Medal


async def setup(bot):
    await bot.add_cog(Medal(bot))
