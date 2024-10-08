from .pplx_api import PerplexityAPI

async def setup(bot):
    await bot.add_cog(PerplexityAPI(bot))

