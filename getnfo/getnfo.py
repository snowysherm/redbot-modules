import os
import discord
import aiohttp
import asyncio
from redbot.core import commands
import io  # Needed for byte stream handling
import re  # Needed for regex processing to strip ASCII art


class getnfo(commands.Cog):
    """Cog to fetch NFOs for warez releases using the xrel.to and predb.net APIs"""

    def __init__(self, bot):
        self.bot = bot
        self.client_id, self.client_secret = self.load_credentials()
        self.api_base_url = "https://api.xrel.to/v2"
        self.token = None
        self.token_expires_at = 0  # Timestamp when the token expires
        self.bot.loop.create_task(self.schedule_token_refresh())  # Schedule token refresh

    def load_credentials(self):
        """Load client ID and client secret from a .env file."""
        script_dir = os.path.dirname(__file__)  # Directory of the current script
        env_path = os.path.join(script_dir, ".env")  # Path to the .env file in the same directory
        if not os.path.exists(env_path):
            print(
                f"No .env file found at {env_path}. Ensure the .env file is in the correct directory."
            )
            return None, None

        with open(env_path, "r") as file:
            lines = file.read().splitlines()
            credentials = {
                line.split("=")[0].strip(): line.split("=")[1].strip() for line in lines
            }
        return credentials.get("CLIENT_ID"), credentials.get("CLIENT_SECRET")

    async def get_token(self):
        """Fetches or reuses the OAuth2 token using Client Credentials Grant."""
        current_time = asyncio.get_event_loop().time()
        if not self.token or current_time >= self.token_expires_at:
            async with aiohttp.ClientSession() as session:
                auth = aiohttp.BasicAuth(self.client_id, self.client_secret)
                data = {"grant_type": "client_credentials", "scope": "viewnfo"}
                async with session.post(
                        self.api_base_url + "/oauth2/token", auth=auth, data=data
                ) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        self.token = token_data.get("access_token")
                        expires_in = token_data.get("expires_in", 3600)
                        self.token_expires_at = current_time + expires_in - 60  # Refresh 1 minute before expiration
                        if not self.token or self.token.count(".") != 2:
                            print("Invalid token format:", self.token)
                            self.token = None  # Reset token if invalid
                    else:
                        print(f"Failed to retrieve token: {response.status}")
                        self.token = None
        return self.token

    async def schedule_token_refresh(self):
        """Schedule token refresh every hour."""
        while True:
            await self.get_token()
            await asyncio.sleep(3600)  # Sleep for 1 hour

    async def fetch_and_send_nfo(self, ctx, headers, release_info, nfo_type):
        """Fetch and send the NFO image from the API."""
        nfo_url = f"{self.api_base_url}/nfo/{nfo_type}.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    nfo_url, headers=headers, params={"id": release_info["id"]}
            ) as nfo_response:
                if nfo_response.status == 200:
                    # Correct handling for image response
                    data = io.BytesIO(await nfo_response.read())
                    await ctx.send(
                        file=discord.File(data, f"{release_info['id']}_nfo.png")
                    )
                elif nfo_response.status == 404:
                    await ctx.send(f"NFO not found for release ID {release_info['id']}.")
                else:
                    await ctx.send(
                        f"Failed to retrieve NFO: {await nfo_response.text()} Status Code: {nfo_response.status}"
                    )

    async def fetch_and_send_nfo_text(self, ctx, release: str):
        # First, construct the URL to fetch NFO link
        url = f"https://api.srrdb.com/v1/nfo/{release}"

        async with aiohttp.ClientSession() as session:
            # Fetching the NFO link
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if not data['nfolink']:  # Check if the nfolink list is empty
                        await ctx.send(f"No NFO could be found.")
                        return

                    nfo_link = data['nfolink'][0]  # Access the first NFO link

                    # Now fetch the actual NFO text
                    async with session.get(nfo_link) as nfo_response:
                        if nfo_response.status == 200:
                            try:
                                nfo_text = await nfo_response.text()
                            except UnicodeDecodeError:
                                # If utf-8 decoding fails, try decoding with latin-1
                                raw_data = await nfo_response.read()
                                nfo_text = raw_data.decode('latin-1', errors='replace')
                            # Process and send the NFO text in chunks to avoid Discord message length limits
                            chunks = []
                            current_chunk = "```"
                            for line in nfo_text.splitlines():
                                if len(current_chunk) + len(line) + 4 > 2000:  # Discord limit is 2000 characters
                                    current_chunk += "```"
                                    chunks.append(current_chunk)
                                    current_chunk = "```" + line + "\n"
                                else:
                                    current_chunk += line + "\n"
                            if current_chunk:
                                current_chunk += "```"
                                chunks.append(current_chunk)

                            # Send each chunk as a separate message
                            for chunk in chunks:
                                await ctx.send(chunk)
                        else:
                            await ctx.send(
                                f"Failed to retrieve NFO content for release {release}. Status Code: {nfo_response.status}")
                else:
                    await ctx.send(f"Failed to retrieve NFO link for release {release}. Status Code: {response.status}")

    @commands.command()
    async def nfo(self, ctx, *, dirname: str):
        token = await self.get_token()
        if not token:
            await ctx.send("Failed to obtain valid authentication token.")
            return

        headers = {"Authorization": f"Bearer {token}"}

        # Reduce error output by handling errors silently unless both fail
        successful = False
        for type_path, nfo_type in [("/release/info.json", "release"), ("/p2p/rls_info.json", "p2p_rls")]:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                        self.api_base_url + type_path,
                        headers=headers,
                        params={"dirname": dirname},
                ) as response:
                    if response.status == 200:
                        release_info = await response.json()
                        if "id" in release_info:
                            await self.fetch_and_send_nfo(
                                ctx, headers, release_info, nfo_type
                            )
                            successful = True
                            break
                    elif response.status == 404:
                        continue  # Try the next path if 404

        if not successful:
            await self.fetch_and_send_nfo_text(ctx, dirname)

    @commands.command()
    async def nfotxt(self, ctx, *, release: str):
        await self.fetch_and_send_nfo_text(ctx, release)


def setup(bot):
    bot.add_cog(getnfo(bot))
