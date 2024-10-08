from .pplx_api import PerplexityAI

async def setup(bot):
    await bot.add_cog(PerplexityAI(bot))

