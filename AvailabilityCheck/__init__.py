from .availabilitychecker import AvailabilityChecker


async def setup(bot):
    await bot.add_cog(AvailabilityChecker(bot))