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
        if message:
            content = message
        else:
            content = ctx.message.content
            to_strip = f"(?m)^(<@!?{self.bot.user.id}>\\s*)"
            content = re.sub(to_strip, "", content)
            if content.lower().startswith("pplx ") or content.lower().startswith("chat "):
                content = content[5:]

        content = content.strip()

        if prompt_insert:
            content = f"{prompt_insert}\n\n{content}"

        return self.sanitize_mentions(ctx, content)

    def sanitize_mentions(self, ctx: commands.Context, content: str) -> str:
        for user in ctx.message.mentions:
            content = content.replace(f'<@{user.id}>', f'@{user.display_name}')
            content = content.replace(f'<@!{user.id}>', f'@{user.display_name}')
        for role in ctx.message.role_mentions:
            content = content.replace(f'<@&{role.id}>', f'@{role.name}')
        for channel in ctx.message.channel_mentions:
            content = content.replace(f'<#{channel.id}>', f'#{channel.name}')
        return content

    @commands.command()
    @checks.is_owner()
    async def getpplxmodel(self, ctx: commands.Context):
        """Get the model for Perplexity AI."""
        model = await self.config.model()
        await ctx.send(f"Perplexity AI model set to `{model}`")

    @commands.command()
    @checks.is_owner()
    async def setpplxmodel(self, ctx: commands.Context, model: str):
        """Set the model for Perplexity AI."""
        if self.client is None:
            self.client = PerplexityClient(key=await self.perplexity_api_key())

        available_models = self.client.models.keys()
        if model not in available_models:
            await ctx.send(f"Invalid model. Available models: {', '.join(available_models)}")
            return

        self.client.model = model
        await self.config.model.set(model)
        await ctx.send(f"Perplexity AI model set to {model}.")

    @commands.command()
    @checks.is_owner()
    async def getpplxtokens(self, ctx: commands.Context):
        """Get the maximum number of tokens for Perplexity AI to generate."""
        max_tokens = await self.config.max_tokens()
        await ctx.send(f"Perplexity AI maximum number of tokens set to `{max_tokens}`")

    @commands.command()
    @checks.is_owner()
    async def setpplxtokens(self, ctx: commands.Context, number: str):
        """Set the maximum number of tokens for Perplexity AI to generate."""
        try:
            await self.config.max_tokens.set(int(number))
            await ctx.send("Perplexity AI maximum number of tokens set.")
        except ValueError:
            await ctx.send("Invalid numeric value for maximum number of tokens.")

    @commands.command()
    @checks.is_owner()
    async def togglepplxmention(self, ctx: commands.Context):
        """Toggle messages to Perplexity AI on mention.
        Defaults to `True`."""
        mention = not await self.config.mention()
        await self.config.mention.set(mention)
        if mention:
            await ctx.send("Enabled sending messages to Perplexity AI on bot mention.")
        else:
            await ctx.send("Disabled sending messages to Perplexity AI on bot mention.")

    @commands.command()
    @checks.is_owner()
    async def togglepplxreply(self, ctx: commands.Context):
        """Toggle messages to Perplexity AI on reply.
        Defaults to `True`."""
        reply = not await self.config.reply()
        await self.config.reply.set(reply)
        if reply:
            await ctx.send("Enabled sending messages to Perplexity AI on bot reply.")
        else:
            await ctx.send("Disabled sending messages to Perplexity AI on bot reply.")

    @commands.command()
    @checks.is_owner()
    async def getpplxpromptinsert(self, ctx: commands.Context):
        """Get the prompt insertion for Perplexity AI."""
        prompt_insert = await self.config.prompt_insert()
        await ctx.send(f"Perplexity AI prompt insertion is set to: `{prompt_insert}`")

    @commands.command()
    @checks.is_owner()
    async def setpplxpromptinsert(self, ctx: commands.Context, *, prompt_insert: str):
        """Set the prompt insertion for Perplexity AI."""
        await self.config.prompt_insert.set(prompt_insert)
        await ctx.send("Perplexity AI prompt insertion set.")

