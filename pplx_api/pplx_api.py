import discord
from discord import Message, ui, ButtonStyle
from redbot.core import Config, checks, commands
from typing import List
import openai
from openai import AsyncOpenAI
import asyncio
import re
import aiohttp

class PerplexityAI(commands.Cog):
    """Send messages to Perplexity AI"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=359554900000)
        default_global = {
            "perplexity_api_key": None,
            "perplexity_api_key_2": None,
            "model": "sonar-reasoning",
            "max_tokens": 2000,
            "prompt": "",
        }
        self.config.register_global(**default_global)

    async def perplexity_api_keys(self):
        return await self.bot.get_shared_api_tokens("perplexity")

    async def upload_to_0x0(self, text: str) -> str:
        url = "https://0x0.st"
        data = aiohttp.FormData()
        data.add_field('file', text, filename='thinking.txt')
        data.add_field('secret', '')
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        return (await response.text()).strip()
                    else:
                        raise Exception(f"Upload failed: HTTP {response.status}")
        except Exception as e:
            raise Exception(f"Upload error: {str(e)}")

    @commands.command(aliases=['pplx'])
    async def perplexity(self, ctx: commands.Context, *, message: str):
        """Send a message to Perplexity AI"""
        await self.do_perplexity(ctx, message)

    async def do_perplexity(self, ctx: commands.Context, message: str):
        async with ctx.typing():
            messages = []
            await self.build_conversation_chain(ctx, message, messages)
            
            # Validate message structure before sending
            if not self.validate_message_roles(messages):
                return await ctx.send("Error: Invalid conversation sequence")

            api_keys = (await self.perplexity_api_keys()).values()
            if not any(api_keys):
                return await ctx.send(f"API keys missing! Use `{ctx.prefix}set api perplexity api_key,api_key_2`")

            try:
                response = await self.call_api(
                    model=await self.config.model(),
                    api_keys=api_keys,
                    messages=messages,
                    max_tokens=await self.config.max_tokens() or 2000
                )
            except Exception as e:
                return await ctx.send(f"API Error: {str(e)}")





            if not response:
                return await ctx.send("No response from API")
                
            content = response.choices[0].message.content
            citations = getattr(response, 'citations', [])
            
            upload_url = None
            think_match = re.search(r'<think>(.*?)</think>', content, re.DOTALL)
            if think_match:
                think_text = think_match.group(1)
                try:
                    upload_url = await self.upload_to_0x0(think_text)
                    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
                except Exception as e:
                    print(f"Failed to upload reasoning: {e}")

            chunks = self.smart_split(content)
            citation_lines = [f"{i+1}. <{url}>" for i, url in enumerate(citations)] if citations else []

            for index, chunk in enumerate(chunks):
                view = None
                if index == len(chunks) - 1 and upload_url:
                    view = self.create_view(upload_url, ctx.guild)
                await ctx.send(chunk, view=view)
                await ctx.typing()            
                await asyncio.sleep(0.5)

            if citation_lines:
                header = "**Quellen:**"
                full_message = f"{header}\n" + "\n".join(citation_lines)
                await ctx.send(full_message)

    def create_view(self, upload_url, guild):
        """Helper to create a view with the reasoning button."""
        bigbrain_emoji = discord.utils.get(guild.emojis, name="bigbrain") if guild else None
        view = ui.View()
        button = ui.Button(
            style=ButtonStyle.primary,
            label="Reasoning",
            url=upload_url,
            emoji=bigbrain_emoji or "🧠"
        )
        view.add_item(button)
        return view

    async def build_conversation_chain(self, ctx: commands.Context, message: str, messages: list):
        """Builds message chain according to Perplexity API requirements"""
        # Add system prompt first if configured
        if prompt := await self.config.prompt():
            messages.append({"role": "system", "content": prompt})
        
        # Track conversation history
        history = []
        
        # Process message references
        current_msg = ctx.message
        for _ in range(5):  # Max 5 levels of reply nesting
            if current_msg.reference and current_msg.reference.message_id:
                try:
                    parent_msg = await ctx.channel.fetch_message(current_msg.reference.message_id)
                    history.insert(0, parent_msg)
                    current_msg = parent_msg
                except:
                    break
            else:
                break
        
        # Add historical messages with proper roles
        for msg in history:
            role = "assistant" if msg.author == self.bot.user else "user"
            content = msg.clean_content
            
            # Remove bot mentions
            if role == "user":
                content = re.sub(f"<@!?{self.bot.user.id}>", "", content).strip()
            
            # Merge consecutive user messages
            if messages and messages[-1]["role"] == role == "user":
                messages[-1]["content"] += f"\n\n{content}"
            else:
                messages.append({"role": role, "content": content})
        
        # Add current message
        messages.append({"role": "user", "content": message})

    def validate_message_roles(self, messages: list) -> bool:
        """Ensures valid role sequence: system -> user -> assistant -> user ..."""
        valid = True
        last_role = None
        
        for msg in messages:
            current_role = msg["role"]
            
            if current_role == "system":
                if last_role is not None:
                    valid = False
            elif current_role == "user":
                if last_role == "user":
                    valid = False
            elif current_role == "assistant":
                if last_role not in ["user", "system"]:
                    valid = False
            
            last_role = current_role
        
        return valid

    async def call_api(self, model: str, api_keys: list, messages: List[dict], max_tokens: int):
        for key in filter(None, api_keys):
            try:
                client = AsyncOpenAI(api_key=key, base_url="https://api.perplexity.ai")
                return await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens
                )
            except Exception as e:
                # Enhanced error logging
                error_detail = ""
                if hasattr(e, 'response'):
                    try:
                        error_detail = f" | Details: {await e.response.text()}"
                    except:
                        error_detail = " | Couldn't read error details"
                print(f"API Error: {str(e)}{error_detail}")
        return None

    def smart_split(self, text: str, limit: int = 1950) -> List[str]:
            chunks = []
            current_chunk = []
            current_length = 0
            in_code_block = False
        
            lines = text.split('\n')
            for line in lines:
                line_stripped = line.strip()
                
                # Toggle code block state on lines with ```
                if line_stripped.startswith('```'):
                    in_code_block = not in_code_block
        
                new_length = current_length + len(line) + 1  # +1 for newline
                
                if new_length > limit:
                    # Finalize current chunk
                    chunk = '\n'.join(current_chunk)
                    
                    # Add code block closure if needed
                    if in_code_block:
                        chunk += '\n```'
                        # Next chunk should start with code block opener
                        chunks.append(chunk)
                        current_chunk = ['```', line]
                        current_length = len('```\n') + len(line) + 1
                    else:
                        chunks.append(chunk)
                        current_chunk = [line]
                        current_length = len(line) + 1
                else:
                    current_chunk.append(line)
                    current_length = new_length
        
            # Add remaining content
            if current_chunk:
                chunk = '\n'.join(current_chunk)
                if in_code_block:
                    chunk += '\n```'
                chunks.append(chunk)
        
            return chunks

    # async def build_message_chain(self, ctx: commands.Context, messages: List[dict], message: Message, message_text: str = None, reply_count=0):
    #     if message.reference and message.reference.resolved is None:
    #         message = await ctx.channel.fetch_message(message.id)

    #     # Determine role and process content
    #     role = "assistant" if message.author == self.bot.user else "user"
    #     content = message_text if message_text else message.clean_content
        
    #     # Remove bot mention if present
    #     mention_pattern = f"(?m)^(<@!?{self.bot.user.id}>)"
    #     if re.search(mention_pattern, content):
    #         content = re.sub(mention_pattern, "", content).strip()

    #     # Merge consecutive user messages
    #     if role == "user" and messages and messages[-1]["role"] == "user":
    #         messages[-1]["content"] += f"\n\n{content}"
    #     else:
    #         messages.append({"role": role, "content": content})

    #     # Recursively process message references (up to 5 levels deep)
    #     if reply_count < 5 and message.reference and message.reference.resolved:
    #         reply_count += 1
    #         await self.build_message_chain(
    #             ctx, messages, message.reference.resolved, 
    #             None, reply_count
    #         )

        # Reverse to get chronological order and add system prompt
        messages.reverse()
        if prompt := await self.config.prompt():
            messages.insert(0, {"role": "system", "content": prompt})
    
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
