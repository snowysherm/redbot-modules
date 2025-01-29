from discord import Message
from redbot.core import Config, checks, commands
from typing import List
import openai
from openai import OpenAI

class PerplexityAI(commands.Cog):
    """Send messages to Perplexity AI"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=3.595549e+11)
        default_global = {
            "perplexity_api_key": None,
            "perplexity_api_key_2": None,
            "model": "llama-3.1-sonar-small-128k-chat",
            "max_tokens": 400,
            "prompt": "",
        }
        self.config.register_global(**default_global)
        self.client = None

    async def perplexity_api_keys(self):
        perplexity_keys = await self.bot.get_shared_api_tokens("perplexity")
        api_key = perplexity_keys.get("api_key")
        api_key_2 = perplexity_keys.get("api_key_2")

        if api_key is None:
            api_key = await self.config.perplexity_api_key()
        if api_key_2 is None:
            api_key_2 = await self.config.perplexity_api_key_2()

        if api_key is not None:
            await self.bot.set_shared_api_tokens("perplexity", api_key=api_key)
            await self.config.perplexity_api_key.set(None)
        if api_key_2 is not None:
            await self.bot.set_shared_api_tokens("perplexity", api_key_2=api_key_2)
            await self.config.perplexity_api_key_2.set(None)

        return api_key, api_key_2

    @commands.command(aliases=['pplx'])
    async def perplexity(self, ctx: commands.Context, *, message: str):
        """Send a message to Perplexity AI."""
        await self.do_perplexity(ctx, message)

    async def do_perplexity(self, ctx: commands.Context, message: str):
        await ctx.typing()
        api_key, api_key_2 = await self.perplexity_api_keys()

        if api_key is None and api_key_2 is None:
            prefix = ctx.prefix if ctx.prefix else "[p]"
            await ctx.send(f"Perplexity API keys not set. Use `{prefix}set api perplexity api_key,api_key_2 ,`.\nAPI keys may be acquired from: https://www.perplexity.ai/")
            return

        model = await self.config.model()
        max_tokens = await self.config.max_tokens()
        messages = [{"role": "user", "content": message}]
        if prompt := await self.config.prompt():
            messages.insert(0, {"role": "system", "content": prompt})

        reply = await self.call_api(model, api_key, messages, max_tokens)
        
        if reply:
            # DEBUG: Check reply length and chunks
            print(f"[DEBUG] Reply length: {len(reply)}")
            chunks = self.smart_split(reply)
            print(f"[DEBUG] Number of chunks: {len(chunks)}")
            for chunk in chunks:
                await ctx.send(chunk)
        else:
            await ctx.send("No response from Perplexity AI.")

    async def call_api(self, model: str, api_key: str, messages: List[dict], max_tokens: int):
        api_keys = [api_key, (await self.perplexity_api_keys())[1]]
        for key in filter(None, api_keys):
            try:
                self.client = OpenAI(api_key=key, base_url="https://api.perplexity.ai")
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content or "Empty response."
            except Exception as e:
                continue
        return "All API keys failed."

    def smart_split(self, text: str, char_limit: int = 2000) -> List[str]:
        # Bruteforce split every 2000 characters
        return [text[i:i+char_limit] for i in range(0, len(text), char_limit)]

    # Configuration commands remain unchanged
    @commands.command()
    @checks.is_owner()
    async def getperplexitymodel(self, ctx: commands.Context):
        """Get the model for Perplexity AI."""
        await ctx.send(f"Model: {await self.config.model()}")

    @commands.command()
    @checks.is_owner()
    async def setperplexitymodel(self, ctx: commands.Context, model: str):
        """Set the model for Perplexity AI."""
        await self.config.model.set(model)
        await ctx.tick()

    @commands.command()
    @checks.is_owner()
    async def getperplexitytokens(self, ctx: commands.Context):
        """Get the maximum number of tokens for Perplexity AI to generate."""
        await ctx.send(f"Max tokens: {await self.config.max_tokens()}")

    @commands.command()
    @checks.is_owner()
    async def setperplexitytokens(self, ctx: commands.Context, number: int):
        """Set the maximum number of tokens for Perplexity AI to generate."""
        await self.config.max_tokens.set(number)
        await ctx.tick()

    @commands.command()
    @checks.is_owner()
    async def getperplexityprompt(self, ctx: commands.Context):
        """Get the prompt for Perplexity AI."""
        await ctx.send(f"Prompt: {await self.config.prompt()}")

    @commands.command()
    @checks.is_owner()
    async def setperplexityprompt(self, ctx: commands.Context, *, prompt: str):
        """Set the prompt for Perplexity AI."""
        await self.config.prompt.set(prompt)
        await ctx.tick()

def setup(bot):
    bot.add_cog(PerplexityAI(bot))