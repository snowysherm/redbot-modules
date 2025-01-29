from discord import Message
from redbot.core import Config, checks, commands
from typing import List
import openai
from openai import OpenAI
import asyncio

class PerplexityAI(commands.Cog):
    """Send messages to Perplexity AI"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=359554900000)
        default_global = {
            "perplexity_api_key": None,
            "perplexity_api_key_2": None,
            "model": "llama-3.1-sonar-small-128k-chat",
            "max_tokens": 2000,
            "prompt": "",
        }
        self.config.register_global(**default_global)

    async def perplexity_api_keys(self):
        return await self.bot.get_shared_api_tokens("perplexity")

    @commands.command(aliases=['pplx'])
    async def perplexity(self, ctx: commands.Context, *, message: str):
        """Send a message to Perplexity AI"""
        await self.do_perplexity(ctx, message)

    async def do_perplexity(self, ctx: commands.Context, message: str):
        # Start persistent typing
        async with ctx.typing():
            # Get API response
            api_keys = (await self.perplexity_api_keys()).values()
            if not any(api_keys):
                prefix = ctx.prefix if ctx.prefix else "[p]"
                return await ctx.send(f"API keys missing! Use `{prefix}set api perplexity api_key,api_key_2`")

            model = await self.config.model()
            max_tokens = await self.config.max_tokens() or 2000
            messages = [{"role": "user", "content": message}]
            
            if prompt := await self.config.prompt():
                messages.insert(0, {"role": "system", "content": prompt})

            reply = await self.call_api(model, api_keys, messages, max_tokens)
            if not reply:
                return await ctx.send("No response from API")
                
            chunks = self.smart_split(reply)

            # Create a task to keep typing active
            typing_task = self.bot.loop.create_task(self.keep_typing(ctx.channel))
            
            try:
                for chunk in chunks:
                    await ctx.send(chunk)
                    await asyncio.sleep(0.5)  # Brief pause between messages
            finally:
                typing_task.cancel()  # Stop typing when done

    async def keep_typing(self, channel):
        """Keep sending typing indicator every 8 seconds"""
        while True:
            await channel.trigger_typing()
            await asyncio.sleep(8)  # Discord typing lasts 10 seconds, refresh every 8

    async def call_api(self, model: str, api_keys: list, messages: List[dict], max_tokens: int):
        for key in filter(None, api_keys):
            try:
                client = OpenAI(api_key=key, base_url="https://api.perplexity.ai")
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"API Error: {str(e)}")
        return None

    def smart_split(self, text: str, limit: int = 1950) -> List[str]:
        chunks = []
        while len(text) > 0:
            if len(text) <= limit:
                chunks.append(text)
                break
                
            split_at = text.rfind('\n\n', 0, limit) or \
                       text.rfind('. ', 0, limit) or \
                       text.rfind(' ', 0, limit) or \
                       limit
            chunks.append(text[:split_at].strip())
            text = text[split_at:].lstrip()
        return chunks



    @commands.command()
    @checks.is_owner()
    async def setperplexitytokens(self, ctx: commands.Context, tokens: int):
        """Set max tokens (2000-4000 recommended)"""
        await self.config.max_tokens.set(max(400, min(tokens, 4000)))
        await ctx.tick()

    @commands.command()
    @checks.is_owner()
    async def setperplexitytokens(self, ctx: commands.Context, tokens: int):
        """Set max tokens (2000-4000 recommended)"""
        await self.config.max_tokens.set(max(400, min(tokens, 4000)))
        await ctx.tick()

    @commands.command()
    @checks.is_owner()
    async def getperplexitymodel(self, ctx: commands.Context):
        """Get the model for Perplexity AI."""
        model = await self.config.model()
        await ctx.send(f"Perplexity AI model set to `{model}`")

    @commands.command()
    @checks.is_owner()
    async def setperplexitymodel(self, ctx: commands.Context, model: str):
        """Set the model for Perplexity AI."""
        await self.config.model.set(model)
        await ctx.send("Perplexity AI model set.")

    @commands.command()
    @checks.is_owner()
    async def getperplexitytokens(self, ctx: commands.Context):
        """Get the maximum number of tokens for Perplexity AI to generate."""
        model = await self.config.max_tokens()
        await ctx.send(f"Perplexity AI maximum number of tokens set to `{model}`")

    @commands.command()
    @checks.is_owner()
    async def getperplexityprompt(self, ctx: commands.Context):
        """Get the prompt for Perplexity AI."""
        prompt = await self.config.prompt()
        await ctx.send(f"Perplexity AI prompt is set to: `{prompt}`")

    @commands.command()
    @checks.is_owner()
    async def setperplexityprompt(self, ctx: commands.Context, *, prompt: str):
        """Set the prompt for Perplexity AI."""
        await self.config.prompt.set(prompt)
        await ctx.send("Perplexity AI prompt set.")

def setup(bot):
    bot.add_cog(PerplexityAI(bot))