from redbot.core import commands
import datetime
import asyncio


class GreetingWatcher(commands.Cog):
    gumo_streak = 0
    gumo_users = []

    greetings_map = {
        "gumo": (6, 10),    # 6:00 - 9:59
        "guvomi": (10, 12), # 10:00 - 11:59
        "gumi": (12, 14),   # 12:00 - 13:59
        "gunami": (14, 18), # 14:00 - 17:59
        "guab": (18, 22),   # 18:00 - 21:59
        "guna": (22, 6)     # 22:00 - 5:59
    }

    def __init__(self, bot):
        self.bot = bot

    def is_greeting_correct(self, greeting):
        now = datetime.datetime.now().hour
        
        if greeting not in GreetingWatcher.greetings_map:
            return True
            
        start_hour, end_hour = GreetingWatcher.greetings_map[greeting]
        
        if start_hour > end_hour:
            return now >= start_hour or now < end_hour
        else:
            return start_hour <= now < end_hour

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id != 1264855954743230556:
            return

        if message.author.bot:
            return

        # streak

        if message.author.id not in GreetingWatcher.gumo_users:
            GreetingWatcher.gumo_streak += 1
            GreetingWatcher.gumo_users.append(message.author.id)

            streak = GreetingWatcher.gumo_streak
            if streak < 33:
                if streak == 11:
                    emojis = ["⏸️"]
                elif streak == 22:
                    emojis = ["2️⃣", "🥈"]
                elif streak <= 10:
                    emojis = ["🔟"] if streak == 10 else [ { '0': "0️⃣", '1': "1️⃣", '2': "2️⃣", 
                                                              '3': "3️⃣", '4': "4️⃣", '5': "5️⃣", 
                                                              '6': "6️⃣", '7': "7️⃣", '8': "8️⃣", 
                                                              '9': "9️⃣" }[str(streak)] ]
                else:
                    emojis = [ { '0': "0️⃣", '1': "1️⃣", '2': "2️⃣", 
                                  '3': "3️⃣", '4': "4️⃣", '5': "5️⃣", 
                                  '6': "6️⃣", '7': "7️⃣", '8': "8️⃣", 
                                  '9': "9️⃣" }[d] for d in str(streak) ]
                await asyncio.sleep(0.5)
                for emoji in emojis:
                    await message.add_reaction(emoji)
                    await asyncio.sleep(0.5)
        else:
            if GreetingWatcher.gumo_streak > 0:
                GreetingWatcher.gumo_streak = 0
                GreetingWatcher.gumo_users = []
            if GreetingWatcher.gumo_streak > 2:
                grr = await message.guild.fetch_emoji(1298594465497354260)
                await message.add_reaction(grr)

        # greeting check

        for greeting in GreetingWatcher.greetings_map:
            if greeting in message.content.lower():
                if self.is_greeting_correct(greeting):
                    if greeting == "guna":
                        bedge = await message.guild.fetch_emoji(1311619322187223120)
                        await message.add_reaction(bedge)
                    else:
                        feelsokman = await message.guild.fetch_emoji(1240917116329263135)
                        await message.add_reaction(feelsokman)
                else:
                    warndreieck = await message.guild.fetch_emoji(1304388231835422780)
                    await message.add_reaction(warndreieck)


async def setup(bot):
    await bot.add_cog(GreetingWatcher(bot))