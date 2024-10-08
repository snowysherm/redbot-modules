from discord import Message
from redbot.core import Config, checks, commands
from typing import List
from perplexipy import PerplexityClient
import re

class PerplexityAPI(commands.Cog):
    """Send messages to Perplexity AI"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=359554929893)
        default_global = {
            "model": "llama-3.1-70b-instruct",
            "max_tokens": 400,
            "mention": True,
            "reply": True,
            "prompt_insert": "",
        }
        self.config.register_global(**default_global)
        self.client = None

    async def cog_load(self):
        await self.initialize()

    async def initialize(self):
        perplexity_api_key = await self.perplexity_api_key()
        if perplexity_api_key:
            self.client = PerplexityClient(key=perplexity_api_key)
            model = await self.config.model()
            self.client.model = model

    async def perplexity_api_key(self):
        pplx_keys = await self.bot.get_shared_api_tokens("pplx")
        return pplx_keys.get("api_key")

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot:
            return
        config_mention = await self.config.mention()
        config_reply = await self.config.reply()
        if not config_mention and not config_reply:
            return
        ctx: commands.Context = await self.bot.get_context(message)
        to_strip = f"(?m)^(<@!?{self.bot.user.id}>)"
        is_mention = config_mention and re.search(to_strip, message.content)
        is_reply = False
        if config_reply and message.reference and message.reference.resolved:
            author = getattr(message.reference.resolved, "author")
            if author is not None:
                is_reply = message.reference.resolved.author.id == self.bot.user.id and ctx.me in message.mentions
        if is_mention or is_reply:
            await self.do_pplx(ctx)

    @commands.command(aliases=['chat'])
    async def pplx(self, ctx: commands.Context, *, message: str = None):
        """Send a message to Perplexity AI."""
        await self.do_pplx(ctx, message)

    async def do_pplx(self, ctx: commands.Context, message: str = None):
        await ctx.typing()
        perplexity_api_key = await self.perplexity_api_key()
        if perplexity_api_key is None:
            prefix = ctx.prefix if ctx.prefix else "[p]"
            await ctx.send(f"Perplexity API key not set. Use `{prefix}set api pplx api_key `.")
            return

        if self.client is None:
            self.client = PerplexityClient(key=perplexity_api_key)

        model = await self.config.model()
        self.client.model = model

        prompt = await self.build_prompt(ctx, message)
        try:
            reply = self.client.query(prompt)
            if len(reply) > 2000:
                reply = reply[:1997] + "..."
            await ctx.send(content=reply, reference=ctx.message)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    async def build_prompt(self, ctx: commands.Context, message: str = None) -> str:
        prompt_insert = await self.config.prompt_insert()
        bot_name = ctx.me.name
        user_name = ctx.author.name

        if message:
            content = message
        else:
            content = ctx.message.content
            to_strip = f"(?m)^(<@!?{self.bot.user.id}>\\s*)"
            content = re.sub(to_strip, "", content)
            if content.lower().startswith("pplx ") or content.lower().startswith("chat "):
                content = content[5:]

        content = content.strip()

        system_prompt = (
            f"You are {bot_name}, an AI assistant. "
            f"You are talking to {user_name}. "
            f"Respond to their message in a helpful and friendly manner."
        )

        if prompt_insert:
            system_prompt += f"\n\n{prompt_insert}"

        full_prompt = f"{system_prompt}\n\n{user_name}: {content}\n\n{bot_name}:"

        return self.sanitize_mentions(ctx, full_prompt)

    def sanitize_mentions(self, ctx: commands.Context, content: str) -> str:
        for user in ctx.message.mentions:
            content = content.replace(f'<@{user.id}>', f'@{user.display_name}')
            content = content.replace(f'<@!{user.id}>', f'@{user.display_name}')
        for role in ctx.message.role_mentions:
            content = content.replace(f'<@&{role.id}>', f'@{role.name}')
        for channel in ctx.message.channel_mentions:
            content = content.replace(f'<#{channel.id}>', f'#{channel.name}')
        return content

    # ... (rest of the commands remain the same)

