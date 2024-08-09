import os
import random

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load the .env file that contains your token
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Set the log channel ID directly
LOG_CHANNEL_ID = 1271302668945719439

# Define intents
intents = discord.Intents.default()
intents.message_content = True  # Enable intents to allow the bot to read message content
intents.guilds = True
intents.guild_messages = True

# Create a bot instance with a command prefix and specified intents
bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionary to store strikes for each user
strikes = {}

# Function to log a strike to the log channel
async def log_strike(user_name, strike_count, channel):
    await channel.send(f'{user_name} has {strike_count} strike(s).')

# Function to load strikes from the log channel
async def load_strikes_from_logs(channel):
    global strikes
    async for message in channel.history(limit=1000):  # Adjust the limit as needed
        content = message.content
        if 'has' in content and 'strike(s).' in content:
            parts = content.split(' ')
            user_name = parts[0]
            strike_count = int(parts[2])
            strikes[user_name] = strike_count

# Event handler for when the bot is ready
@bot.event
async def on_ready():
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    
    # Load strikes from the log channel
    await load_strikes_from_logs(log_channel)
    
    # Print current strikes to the console
    print(f'{bot.user} is connected to Discord!')
    print('Current strike information:')
    if strikes:
        for user, count in strikes.items():
            print(f'{user}: {count} strike(s)')
    else:
        print('No strikes recorded.')

# Command that responds with hello
@bot.command(name='hello', help='Responds with hello')
async def hello(ctx):
    response = "Hello!"
    await ctx.send(response)

# Command to add a strike to a user
@bot.command(name='strike', help='Adds a strike to a user. Usage: /strike @username')
async def strike(ctx, user_name: str):
    if user_name in strikes:
        strikes[user_name] += 1
    else:
        strikes[user_name] = 1
    
    response = f'{user_name} has received a strike. Total strikes: {strikes[user_name]}'
    await ctx.send(response)
    
    # Log the strike to the log channel
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    await log_strike(user_name, strikes[user_name], log_channel)

# Command to delete all messages in the current channel
@bot.command(name='nuke', help='Deletes all messages in the current channel.')
@commands.has_permissions(manage_messages=True)
async def nuke(ctx):
    await ctx.channel.purge()
    await ctx.send("Channel nuked! 💣", delete_after=5)  # Send a confirmation message, then delete it after 5 seconds

# Run the bot with the token
bot.run(TOKEN)
