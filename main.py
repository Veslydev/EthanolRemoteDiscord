import discord
import asyncio
import subprocess
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get Discord token from environment
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Global parameters
user_processes = {}

# Function to send embed messages to the user
async def send_embed_to_user(user_id, title, description):
    user = client.get_user(user_id)
    if not user:
        try:
            user = await client.fetch_user(user_id)
        except discord.errors.NotFound:
            user = None
    
    embed = discord.Embed(title=title, description=description, color=discord.Color.green())
    if user:
        if user.avatar:
            embed.set_author(name=user.name, icon_url=user.avatar.url)
        else:
            embed.set_author(name=user.name)
        await user.send(embed=embed)
    else:
        # Handle the case where the user is not found
        print(f"Unable to send DM to user with ID: {user_id}. User not found.")

# Function to read subprocess output
async def read_output(user_id, process):
    while True:
        output = await process.stdout.readline()
        if output == b'':
            break
        output_text = output.decode('utf-8').strip()
        await send_embed_to_user(user_id, "Ethanol Output", output_text)

# Function to read subprocess errors
async def read_error(user_id, process):
    while True:
        error = await process.stderr.readline()
        if error == b'':
            break
        error_text = error.decode('utf-8').strip()
        await send_embed_to_user(user_id, "Ethanol Error", error_text)

@client.event
async def on_ready():
    print(f'Logged in as {client.user.name}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Process DM messages only
    if isinstance(message.channel, discord.DMChannel):
        user_id = message.author.id

        if message.content.startswith('!login'):
            if user_id in user_processes:
                await send_embed_to_user(user_id, "Login Attempt", "The connection is already made!")
                return

            try:
                param = message.content.split(' ')[1]
                param = ''.join(param.split()).replace(';', '')
                process = await asyncio.create_subprocess_exec(
                    'java', '-jar', 'EthanolRemoteClient.jar', param,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE
                )
                user_processes[user_id] = process
                await send_embed_to_user(user_id, "Login Successful", "Ethanol file executed, connecting...")
                
                # Read output and errors asynchronously
                asyncio.create_task(read_output(user_id, process))
                asyncio.create_task(read_error(user_id, process))
            except IndexError:
                await send_embed_to_user(user_id, "Login Error", "Please enter a parameter! For example !login <Auth-Key>")

        elif message.content.startswith('!logout'):
            if user_id not in user_processes:
                await send_embed_to_user(user_id, "Logout Error", "There is no connected Java process.")
                return
            
            process = user_processes.pop(user_id)
            process.terminate()
            await process.wait()
            await send_embed_to_user(user_id, "Logout Successful", "The Java process has been finalized.")

        elif user_id in user_processes:
            process = user_processes[user_id]
            if process.stdin:
                command = message.content.strip()
                process.stdin.write((command + '\n').encode('utf-8'))
                await process.stdin.drain()
            else:
                await send_embed_to_user(user_id, "Command Error", "The Java process is not running or stdin is not available.")
        else:
            await send_embed_to_user(user_id, "Command Error", "You must first connect using the !login command.")

client.run(TOKEN)
