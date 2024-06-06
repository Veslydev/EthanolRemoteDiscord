TOKEN = 'TOKEN'  # Put your bot token here

import discord
import asyncio
import subprocess

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# global parameters
user_processes = {}

async def read_output(user_id, process, channel):
    while True:
        output = await process.stdout.readline()
        if output == b'':
            break
        await channel.send(output.decode('utf-8').strip())

async def read_error(user_id, process, channel):
    while True:
        error = await process.stderr.readline()
        if error == b'':
            break
        await channel.send(error.decode('utf-8').strip())

@client.event
async def on_ready():
    print(f'{client.user} logged in as')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    user_id = message.author.id

    if message.content.startswith('!login'):
        if user_id in user_processes:
            await message.channel.send('The connection is already made!')
            return
        
        try:
            param = message.content.split(' ')[1]
            process = await asyncio.create_subprocess_exec(
                'java', '-jar', 'EthanolRemoteClient.jar', param, # Replace EthanolRemoteClient.jar with your jar file
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE
            )
            user_processes[user_id] = process
            await message.channel.send(f'{message.author.mention} Java jar file executed, connecting...')
            
            # Read output and errors asynchronously
            asyncio.create_task(read_output(user_id, process, message.channel))
            asyncio.create_task(read_error(user_id, process, message.channel))
        except IndexError:
            await message.channel.send('Please enter a parameter! For example !login <Auth-Key>')

    elif message.content.startswith('!logout'):
        if user_id not in user_processes:
            await message.channel.send('There is no connected Java process.')
            return
        
        process = user_processes.pop(user_id)
        process.terminate()
        await process.wait()
        await message.channel.send('The Java process has been finalized.')

    elif user_id in user_processes:
        process = user_processes[user_id]
        if process.stdin:
            command = message.content.strip()
            process.stdin.write((command + '\n').encode('utf-8'))
            await process.stdin.drain()
        else:
            await message.channel.send('The Java process is not running or stdin is not available.')
    else:
        await message.channel.send('You must first connect using the !login command.')

client.run(TOKEN)
