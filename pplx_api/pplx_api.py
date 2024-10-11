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
            "model": "llama-3.1-sonar-small-128k-chat",
            "max_tokens": 400,
            "prompt": "",
        }
        self.config.register_global(**default_global)
        self.client = None

    async def perplexity_api_key(self):
        perplexity_keys = await self.bot.get_shared_api_tokens("perplexity")
        perplexity_api_key = perplexity_keys.get("api_key")
        if perplexity_api_key is None:
            perplexity_api_key = await self.config.perplexity_api_key()
            if perplexity_api_key is not None:
                await self.bot.set_shared_api_tokens("perplexity", api_key=perplexity_api_key)
                await self.config.perplexity_api_key.set(None)
        return perplexity_api_key

    @commands.command(aliases=['pplx'])
    async def perplexity(self, ctx: commands.Context, *, message: str):
        """Send a message to Perplexity AI.
        
        This command allows you to interact with Perplexity AI by sending a message.
        The AI will process your input and provide a response.
        
        Usage:
        !pplx <your message>
        """
        await self.do_perplexity(ctx, message)

    async def do_perplexity(self, ctx: commands.Context, message: str):
        await ctx.typing()
        perplexity_api_key = await self.perplexity_api_key()
        if perplexity_api_key is None:
            prefix = ctx.prefix if ctx.prefix else "[p]"
            await ctx.send(f"Perplexity API key not set. Use `{prefix}set api perplexity api_key `.\nAn API key may be acquired from: https://www.perplexity.ai/")
            return

        model = await self.config.model()
        if model is None:
            await ctx.send("Perplexity AI model not set.")
            return

        max_tokens = await self.config.max_tokens()
        if max_tokens is None:
            await ctx.send("Perplexity AI max_tokens not set.")
            return

        messages = [{"role": "user", "content": message}]
        prompt = await self.config.prompt()
        if prompt:
            messages.insert(0, {"role": "system", "content": prompt})

        # Debug: Show messages sent to Perplexity AI
        # debug_message = "Messages Sent to Perplexity AI:\n"
        # for msg in messages:
        #     debug_message += f"{msg['role'].capitalize()}: {msg['content']}\n\n"
        # await ctx.send(debug_message)

        reply = await self.call_api(
            model=model,
            api_key=perplexity_api_key,
            messages=messages,
            max_tokens=max_tokens
        )

        if reply:
            await ctx.send(reply)
        else:
            await ctx.send("No response was generated from Perplexity AI. Please try again later.")

    async def call_api(self, messages, model: str, api_key: str, max_tokens: int):
        try:
            if self.client is None:
                self.client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.perplexity.ai"
                )
            self.client.api_key = api_key
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens
            )
            reply = response.choices[0].message.content
            if not reply:
                return "The message from Perplexity AI was empty."
            else:
                return reply
        except openai.APIConnectionError as e:
            return f"Failed to connect to Perplexity API: {e}"
        except openai.RateLimitError as e:
            return f"Perplexity API request exceeded rate limit: {e}"
        except openai.AuthenticationError as e:
            return f"Perplexity API returned an Authentication Error: {e}"
        except openai.APIError as e:
            return f"Perplexity API returned an API Error: {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"

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
    async def setperplexitytokens(self, ctx: commands.Context, number: str):
        """Set the maximum number of tokens for Perplexity AI to generate."""
        try:
            await self.config.max_tokens.set(int(number))
            await ctx.send("Perplexity AI maximum number of tokens set.")
        except ValueError:
            await ctx.send("Invalid numeric value for maximum number of tokens.")

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

