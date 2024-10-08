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

        messages = await self.build_messages(ctx, message)
        try:
            reply = self.client.query(messages)
            if len(reply) > 2000:
                reply = reply[:1997] + "..."
            await ctx.send(content=reply, reference=ctx.message)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    async def build_messages(self, ctx: commands.Context, message: str = None) -> List[dict]:
        prompt_insert = await self.config.prompt_insert()
        
        messages = []
        
        if prompt_insert:
            messages.append({"role": "system", "content": prompt_insert})
        
        if message:
            content = message
        else:
            content = ctx.message.content
            to_strip = f"(?m)^(<@!?{self.bot.user.id}>\\s*)"
            content = re.sub(to_strip, "", content)
            if content.lower().startswith('pplx ') or content.lower().startswith('chat '):
                content = content[5:]
        
        messages.append({"role": "user", "content": content.strip()})
        
        return messages

    # ... (rest of the commands remain the same)

