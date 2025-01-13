import os

import discord
import asyncio
import subprocess
import requests
from redbot.core import commands
from discord.ui import View, Button
import io  # Needed for byte stream handling
import json
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')


class getnfo(commands.Cog):
    """Cog to fetch NFOs for warez releases using the xrel.to and predb.net APIs"""

    def __init__(self, bot):
        self.bot = bot
        self.client_id, self.client_secret = self.load_credentials()
        self.xrel_api_base_url = "https://api.xrel.to/v2"
        self.srrdb_api_base_url = "https://api.srrdb.com/v1/nfo/"
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
        """Fetches or reuses the OAuth2 token using Client Credentials Grant with curl."""
        current_time = asyncio.get_event_loop().time()
        logging.debug(f"Current time: {current_time}")
        if not self.token or current_time >= self.token_expires_at:
            curl_command = [
                "curl",
                "-X", "POST",
                f"{self.xrel_api_base_url}/oauth2/token",
                "--data", "grant_type=client_credentials",
                "--data", "scope=viewnfo",
                "--user", f"{self.client_id}:{self.client_secret}"
            ]

            try:
                result = subprocess.run(curl_command, capture_output=True, text=True)
                logging.debug(f"Curl stdout: {result.stdout}")
                logging.debug(f"Curl stderr: {result.stderr}")

                if result.returncode == 0:
                    token_data = json.loads(result.stdout)
                    self.token = token_data.get("access_token")
                    expires_in = token_data.get("expires_in", 3600)
                    self.token_expires_at = current_time + expires_in - 60  # Refresh 1 minute before expiration
                    logging.debug(f"Token: {self.token}")
                    logging.debug(f"Token expires at: {self.token_expires_at}")
                    if not self.token or self.token.count(".") != 2:
                        logging.error("Invalid token format: %s", self.token)
                        self.token = None  # Reset token if invalid
                else:
                    logging.error(f"Failed to retrieve token: {result.stderr}")
                    self.token = None
            except Exception as e:
                logging.error(f"Error occurred during curl command: {e}")
                self.token = None
        return self.token

    async def schedule_token_refresh(self):
        """Schedule token refresh every hour."""
        while True:
            await self.get_token()
            await asyncio.sleep(3600)  # Sleep for 1 hour

    async def fetch_releases(self, ctx, release):
        responses = {
            'srrdb': await self.fetch_srrdb_response(ctx, release),
            'xrel': await self.fetch_xrel_response(ctx, release)
        }
        return responses

    async def fetch_srrdb_response(self, ctx, release):
        url = f"{self.srrdb_api_base_url}{release}"

        response = requests.get(url)

        if response.status_code == 200:
            if response.json()['release'] is None:
                return {
                    'success': None,
                    'button': False
                }

        button = Button(label="View on srrDB", url=f"https://www.srrdb.com/release/details/{release}")

        return {
            'success': True,
            'button': button
        }

    async def fetch_xrel_response(self, ctx, release):
        token = await self.get_token()

        if not token:
            await ctx.send("Failed to obtain valid authentication token.")
            return

        headers = {"Authorization": f"Bearer {token}"}

        return {
            'success': True,
            'button': button
        }

    @commands.command()
    async def nfo(self, ctx, *, release: str):
        await ctx.typing()
        await self.fetch_releases(self, ctx, release)

    def setup(bot):
        bot.add_cog(getnfo(bot))
