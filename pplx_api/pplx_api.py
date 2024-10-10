from discord import Message
from redbot.core import Config, checks, commands
from typing import List
import openai
from openai import OpenAI
import re

class PerplexityAI(commands.Cog):
    """Send messages to Perplexity AI"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=3.595549e+11)
        default_global = {
            "perplexity_api_key": None,
            "model": "llama-3.1-sonar-small-128k-chat",
            "max_tokens": 400,
            "mention": True,
            "reply": True,
            "prompt_insert": "",
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
            await self.do_perplexity(ctx)

    @commands.command(aliases=['pplx'])
    async def perplexity(self, ctx: commands.Context, *, message: str):
        """Send a message to Perplexity AI."""
        await self.do_perplexity(ctx, message)

    async def do_perplexity(self, ctx: commands.Context, message: str = None):
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
        messages = []
        await self.build_messages(ctx, messages, ctx.message, message)
        
        formatted_messages = "\n\n".join([f"**{msg['role'].capitalize()}:** {msg['content']}" for msg in messages])

        await ctx.send(f"**Messages Sent to Perplexity AI:**\n{formatted_messages}")
        
        reply = await self.call_api(
            model=model,
            api_key=perplexity_api_key,
            messages=messages,
            max_tokens=max_tokens
        )
        if reply:
            await ctx.send(
                content=reply,
                reference=ctx.message
            )
        else:
            await ctx.send("No response was generated from Perplexity AI. Please try again later.")

    async def build_messages(self, ctx: commands.Context, messages: List[Message], message: Message, messageText: str = None):
        role = "assistant" if message.author.id == self.bot.user.id else "user"
        content = messageText if messageText else message.clean_content
        to_strip = f"(?m)^(<@!?{self.bot.user.id}>)"
        is_mention = re.search(to_strip, message.content)
        if is_mention:
            content = content[len(ctx.me.display_name) + 2 :]
        if role == "user" and content.startswith('pplx '):
            content = content[5:]
        messages.insert(0, {"role": role, "content": content })
        
        if message.reference and message.reference.resolved:
            await self.build_messages(ctx, messages, message.reference.resolved)
        else: #we are finished, now we insert the prompt
            prompt_insert = await self.config.prompt_insert()
            if prompt_insert:
                messages.insert(0, {"role": "system", "content": prompt_insert })
            

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
    async def toggleperplexitymention(self, ctx: commands.Context):
        """Toggle messages to Perplexity AI on mention."""
        mention = not await self.config.mention()
        await self.config.mention.set(mention)
        if mention:
            await ctx.send("Enabled sending messages to Perplexity AI on bot mention.")
        else:
            await ctx.send("Disabled sending messages to Perplexity AI on bot mention.")

    @commands.command()
    @checks.is_owner()
    async def toggleperplexityreply(self, ctx: commands.Context):
        """Toggle messages to Perplexity AI on reply."""
        reply = not await self.config.reply()
        await self.config.reply.set(reply)
        if reply:
            await ctx.send("Enabled sending messages to Perplexity AI on bot reply.")
        else:
            await ctx.send("Disabled sending messages to Perplexity AI on bot reply.")

    @commands.command()
    @checks.is_owner()
    async def getperplexitypromptinsert(self, ctx: commands.Context):
        """Get the prompt insertion for Perplexity AI."""
        prompt_insert = await self.config.prompt_insert()
        await ctx.send(f"Perplexity AI prompt insertion is set to: `{prompt_insert}`")

    @commands.command()
    @checks.is_owner()
    async def setperplexitypromptinsert(self, ctx: commands.Context, *, prompt_insert: str):
        """Set the prompt insertion for Perplexity AI."""
        await self.config.prompt_insert.set(prompt_insert)
        await ctx.send("Perplexity AI prompt insertion set.")

def setup(bot):
    bot.add_cog(PerplexityAI(bot))

