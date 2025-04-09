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
            "perplexity_api_key_3": None,
            "model": "sonar-reasoning-pro",
            "max_tokens": 8000,
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
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, headers=headers) as response:
                    if response.status == 200:
                        return (await response.text()).strip()
                    else:
                        raise Exception(f"Upload failed: HTTP {response.status}")
        except Exception as e:
            raise Exception(f"Upload error: {str(e)}")

    @commands.command(aliases=['pplx'])
    async def perplexity(self, ctx: commands.Context, *, message: str = ""):
        """Send a message to Perplexity AI, combining referenced message and additional text."""
        question = await self._get_question(ctx, message)
        if not question:
            await ctx.send("Please provide a question either as text or by replying to a message.")
            return

        await self.do_perplexity(ctx, question)

    @commands.command(aliases=['pplxdeep'])
    async def perplexitydeep(self, ctx: commands.Context, *, message: str = ""):
        """Send a message to Perplexity AI using the sonar-deep-research model for more thorough responses."""
        question = await self._get_question(ctx, message)
        if not question:
            await ctx.send("Please provide a question either as text or by replying to a message.")
            return

        await self.do_perplexity(ctx, question, model="sonar-deep-research")

    async def _get_question(self, ctx: commands.Context, message: str = "") -> str:
        """Extract question from reference and additional text."""
        question = ""

        # Check if the command is invoked as a reply
        if ctx.message.reference:
            ref = ctx.message.reference
            try:
                referenced_msg = ref.resolved or await ctx.channel.fetch_message(ref.message_id)
            except discord.NotFound:
                await ctx.send("The referenced message could not be found.")
                return ""
            except discord.Forbidden:
                await ctx.send("I don't have permission to access that message.")
                return ""
            except discord.HTTPException as e:
                await ctx.send(f"An error occurred: {str(e)}")
                return ""

            # Validate referenced message
            if isinstance(referenced_msg, discord.DeletedReferencedMessage):
                await ctx.send("The referenced message was deleted.")
                return ""
            if not isinstance(referenced_msg, discord.Message) or not referenced_msg.content.strip():
                await ctx.send("The referenced message has no text content.")
                return ""

            question = referenced_msg.content.strip()

        # Combine with additional text if provided
        additional_text = message.strip()
        if additional_text:
            question = f"{question} {additional_text}" if question else additional_text

        return question

    async def do_perplexity(self, ctx: commands.Context, message: str, model: str = None):
        async with ctx.typing():
            api_keys = (await self.perplexity_api_keys()).values()
            if not any(api_keys):
                prefix = ctx.prefix if ctx.prefix else "[p]"
                return await ctx.send(f"API keys missing! Use `{prefix}set api perplexity api_key,api_key_2,api_key_3`")

            # Use provided model or fall back to configured model
            if model is None:
                model = await self.config.model()
            max_tokens = await self.config.max_tokens() or 8000
            messages = [{"role": "user", "content": message}]

            if prompt := await self.config.prompt():
                messages.insert(0, {"role": "system", "content": prompt})

            await ctx.send(f"Debug: Using model: `{model}` with token limit: `{max_tokens}`")

            response = await self.call_api(model, api_keys, messages, max_tokens)
            if not response:
                return await ctx.send("No response from API")

            content = response.choices[0].message.content
            citations = getattr(response, 'citations', [])

            # ADD EXTENSIVE DEBUGGING
            debug_info = [
                f"**Content Analysis:**",
                f"Total content length: {len(content)}",
                f"Contains <think> tag: {'<think>' in content}",
                f"Contains </think> tag: {'</think>' in content}",
            ]

            # Find tag positions if they exist
            if '<think>' in content and '</think>' in content:
                start_pos = content.find('<think>')
                end_pos = content.find('</think>')
                debug_info.append(f"<think> position: {start_pos}")
                debug_info.append(f"</think> position: {end_pos}")
                debug_info.append(f"Content between tags length: {end_pos - start_pos - len('<think>')}")
                debug_info.append(f"First 100 chars after <think>: {content[start_pos + 7:start_pos + 107]}...")

            await ctx.send("\n".join(debug_info))

            # Try regex match with explicit reporting
            upload_url = None
            think_match = re.search(r'<think>(.*?)</think>', content, re.DOTALL)

            if think_match:
                await ctx.send("**REGEX MATCH FOUND!** Extracting thinking content...")
                think_text = think_match.group(1)
                await ctx.send(f"Extracted thinking content length: {len(think_text)}")

                # Try the upload
                try:
                    await ctx.send("Attempting to upload thinking content...")
                    upload_url = await self.upload_to_0x0(think_text)
                    await ctx.send(f"Upload successful! URL: `{upload_url}`")

                    # Try content replacement
                    before_length = len(content)
                    old_content = content
                    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
                    after_length = len(content)

                    await ctx.send(f"Content length before removal: {before_length}")
                    await ctx.send(f"Content length after removal: {after_length}")
                    await ctx.send(f"Difference: {before_length - after_length}")
                    await ctx.send(f"Tags still present after removal: {'<think>' in content or '</think>' in content}")

                    # Fallback to manual removal if regex didn't work
                    if '<think>' in content or '</think>' in content:
                        await ctx.send("Regex substitution failed! Trying manual removal...")
                        start_idx = old_content.find('<think>')
                        end_idx = old_content.find('</think>') + len('</think>')
                        content = old_content[:start_idx] + old_content[end_idx:]
                        await ctx.send(f"Manual removal result length: {len(content)}")
                        await ctx.send(f"Tags still present: {'<think>' in content or '</think>' in content}")
                except Exception as e:
                    await ctx.send(f"**ERROR uploading reasoning**: {str(e)}")
            else:
                await ctx.send("**WARNING: NO REGEX MATCH FOUND for <think>...</think>**")

                # Try manual extraction as fallback
                if '<think>' in content and '</think>' in content:
                    await ctx.send("Attempting alternative manual extraction...")
                    start_idx = content.find('<think>')
                    end_idx = content.find('</think>') + len('</think>')

                    think_text = content[start_idx + len('<think>'):content.find('</think>')]
                    await ctx.send(f"Manually extracted thinking content length: {len(think_text)}")

                    try:
                        upload_url = await self.upload_to_0x0(think_text)
                        await ctx.send(f"Manual upload successful! URL: `{upload_url}`")
                        content = content[:start_idx] + content[end_idx:]
                    except Exception as e:
                        await ctx.send(f"**ERROR in manual upload**: {str(e)}")

            # Test button creation explicitly
            if upload_url:
                test_view = self.create_view(upload_url, ctx.guild)
                await ctx.send("Testing button display:", view=test_view)

            chunks = self.smart_split(content)
            await ctx.send(f"Content split into {len(chunks)} chunks")

            # Send content chunks with button on the last one if applicable
            for index, chunk in enumerate(chunks):
                view = None
                if index == len(chunks) - 1 and upload_url:
                    await ctx.send(f"Creating button view for URL: {upload_url}")
                    view = self.create_view(upload_url, ctx.guild)

                await ctx.send(f"**CHUNK {index + 1}/{len(chunks)}**")
                await ctx.send(chunk, view=view)
                await ctx.typing()
                await asyncio.sleep(0.5)

            # Send citations separately if any exist
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

    async def call_api(self, model: str, api_keys: list, messages: List[dict], max_tokens: int):
        for key in filter(None, api_keys):
            try:
                client = AsyncOpenAI(api_key=key, base_url="https://api.perplexity.ai")
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens
                )
                return response
            except Exception as e:
                print(f"API Error: {str(e)}")
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
                    current_length = len('```')
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

    @commands.command()
    @checks.is_owner()
    async def setperplexitytokens(self, ctx: commands.Context, tokens: int):
        """Set max tokens (2000-4000 recommended)"""
        await self.config.max_tokens.set(max(400, min(tokens, 8000)))
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
        tokens = await self.config.max_tokens()
        await ctx.send(f"Perplexity AI maximum number of tokens set to `{tokens}`")

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
