import os
import tarfile

import discord
import aiohttp
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
        """Fetches or reuses the OAuth2 token using Client Credentials Grant with curl."""
        current_time = asyncio.get_event_loop().time()
        logging.debug(f"Current time: {current_time}")
        if not self.token or current_time >= self.token_expires_at:
            curl_command = [
                "curl",
                "-X", "POST",
                f"{self.api_base_url}/oauth2/token",
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


    async def fetch_xrel(self, ctx, headers, release_info, nfo_type, release_url, is_scene):
        """Fetch and send the NFO image from the API."""
        nfo_url = f"{self.api_base_url}/nfo/{nfo_type}.json"
        
        # Construct the curl command
        curl_command = [
            "curl", "-s",
            "-H", f"Authorization: Bearer {headers['Authorization']}",
            "-G", nfo_url,
            "--data-urlencode", f"id={release_info['id']}"
        ]
        
        # Log the curl command
        log_command = ' '.join(curl_command)
        logging.debug(f"Curl command: {log_command}")
        
        # Execute the curl command
        response = subprocess.run(curl_command, capture_output=True)
        nfo_response_content = response.stdout

        # Log raw response
        logging.debug(f"Raw NFO response: {nfo_response_content.decode('utf-8', errors='ignore')}")
        
        if response.returncode == 0 and nfo_response_content:
            try:
                data = io.BytesIO(nfo_response_content)
                view = View()
                if is_scene:
                    srrdb_button = Button(label="View on srrDB", url=f"https://www.srrdb.com/release/details/{release_info['dirname']}")
                    view.add_item(srrdb_button)
                xrel_button = Button(label="View on xREL", url=release_url)
                view.add_item(xrel_button)

                await ctx.send(file=discord.File(data, f"{release_info['id']}_nfo.png"), view=view)
            except Exception as e:
                logging.error(f"Failed to process NFO response: {e}")
                await ctx.send("Failed to process NFO response.")
        else:
            await ctx.send(f"NFO not found for release ID {release_info['id']} or failed to retrieve NFO. Status Code: {response.returncode}")

    async def fetch_srrdb(self, ctx, release: str):
        # First, construct the URL to fetch NFO link
        url = f"https://api.srrdb.com/v1/nfo/{release}"

        response = requests.get(url)

        if response.status_code == 200:
            if response.json()['release'] is None:
                return False
            nfo_response = requests.get(response.json()['nfolink'][0])
            current_directory = os.path.dirname(os.path.abspath(__file__))
            file_name = 'downloaded_nfo'
            file_path = os.path.join(current_directory, file_name)
            with open(file_path + '.nfo', "wb") as file:
                file.write(nfo_response.content)

            infekt_exe = os.path.join(current_directory, "iNFEKT", "infekt-cli")
            nfo_file_path = os.path.join(current_directory, f"{file_name}")

            flags_and_arguments = [
                '--png', nfo_file_path + '.nfo',
                '-W', '15',
                '-H', '25',
                '-R', '15',
                '-G', '808080'
            ]

            try:
                result = subprocess.run([infekt_exe] + flags_and_arguments, capture_output=True, text=True)

                print("Return code:", result.returncode)
                print("Default output:", result.stdout)
                print("Error output:", result.stderr)
            except Exception as e:
                print(f"Error occurred: {e}")

            view = View()
            button = Button(label="View on srrDB", url=f"https://www.srrdb.com/release/details/{release}")
            view.add_item(button)
            with open(file_path + '.png', "rb") as fp:
                await ctx.send(
                    file=discord.File(fp, 'downloaded_nfo.png'),
                    view=view,
                )
            os.remove(nfo_file_path + '.nfo')
            os.remove(nfo_file_path + '.png')

            return True

        else:
            await ctx.send(f"Failed to retrieve NFO: {response.text} Status Code: {response.status_code}")

            return False

    @commands.command()
    async def nfo(self, ctx, *, dirname: str):
        await ctx.typing()
        token = await self.get_token()
        if not token:
            await ctx.send("Failed to obtain valid authentication token.")
            return

        headers = {"Authorization": f"Bearer {token}"}

        if not (await self.fetch_srrdb(ctx, dirname)):
            for type_path, nfo_type in [("/release/info.json", "release"), ("/p2p/rls_info.json", "p2p_rls")]:
                url = self.api_base_url + type_path
                curl_command = ["curl", "-s", "-H", f"Authorization: Bearer {token}", "-G", url, "--data-urlencode", f"dirname={dirname}"]
                

                response = subprocess.run(curl_command, capture_output=True)
                if response.returncode == 0:
                    raw_response = response.stdout.decode('utf-8')
                    
                    # Log raw response
                    logging.debug(f"Raw response: {raw_response}")

                    try:
                        release_info = json.loads(raw_response)
                    except json.JSONDecodeError:
                        await ctx.send("Failed to parse JSON response.")
                        return
                    
                    logging.debug(f"Release info: {release_info}")
                    
                    if "ext_info" in release_info and "link_href" in release_info["ext_info"]:
                        release_url = release_info["ext_info"]["link_href"]
                        is_scene = (nfo_type == "release")
                        await self.fetch_xrel(ctx, headers, release_info, nfo_type, release_url, is_scene)
                        break
                elif response.returncode == 404:
                    if nfo_type == "p2p_rls":
                        await ctx.send("Arr, Jerome konnte für deinen Release leider weit und breit keine NFO finden! Nicht mal in Davy Jones' Spind...")
                    continue

    def setup(bot):
        bot.add_cog(getnfo(bot))
