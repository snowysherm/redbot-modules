from discord import Message
from redbot.core import Config, checks, commands
from typing import List, Dict
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
        self.config.register_user(conversation=[])
        self.client = None

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

        model = await self.config.model()
        max_tokens = await self.config.max_tokens()

        if self.client is None:
            self.client = PerplexityClient(key=perplexity_api_key)

        conversation = await self.config.user(ctx.author).conversation()
        prompt = await self.build_prompt(ctx, message, conversation)
        
        try:
            reply = self.client.query(prompt)
            if len(reply) > 2000:
                reply = reply[:1997] + "..."
            await ctx.send(content=reply, reference=ctx.message)
            
            conversation.append({"role": "user", "content": message or ctx.message.clean_content})
            conversation.append({"role": "assistant", "content": reply})
            await self.config.user(ctx.author).conversation.set(conversation[-10:])  # Keep last 10 messages
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    async def build_prompt(self, ctx: commands.Context, message: str = None, conversation: List[Dict[str, str]]) -> str:
        prompt_insert = await self.config.prompt_insert()
        content = message if message else ctx.message.clean_content
        
        # Handle mentions and command prefixes
        to_strip = f"(?m)^(<@!?{self.bot.user.id}>\\s*)|(pplx\\s+)|(chat\\s+)"
        content = re.sub(to_strip, "", content, flags=re.IGNORECASE).strip()
        
        full_prompt = prompt_insert + "\n\n" if prompt_insert else ""
        for msg in conversation:
            full_prompt += f"{msg['role'].capitalize()}: {msg['content']}\n\n"
        full_prompt += f"User: {content}\nAssistant:"
        
        return full_prompt

    @commands.command()
    async def pplxreset(self, ctx: commands.Context):
        """Reset your conversation history with Perplexity AI."""
        await self.config.user(ctx.author).conversation.set([])
        await ctx.send("Your conversation history has been reset.")

    # ... (other commands remain the same)

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

    # ... (other commands remain the same)

