#!./bot-env/bin/python3

import os
import random

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load the .env file that contains your token
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Set the log channel ID directly
LOG_CHANNEL_ID = 1271302668945719439  # Replace with your actual log channel ID

# Define intents
intents = discord.Intents.default()
intents.message_content = True  # Enable intents to allow the bot to read message content
intents.guilds = True
intents.guild_messages = True
intents.members = True  # Required to fetch member list

# Create a bot instance with a command prefix and specified intents
bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionary to store strikes for each user by their user ID
strikes = {}
# Dictionary to store members by name for quick lookup
members = {}

# Function to log a strike to the log channel
async def log_strike(user, strike_count, channel):
    embed = discord.Embed(title="Strike Logged", color=discord.Color.red())
    embed.add_field(name="User", value=user.mention, inline=True)
    embed.add_field(name="Total Strikes", value=str(strike_count), inline=True)
    await channel.send(embed=embed)

# Function to load strikes from the log channel
async def load_strikes_from_logs(channel):
    global strikes
    strikes.clear()  # Clear existing strikes to avoid duplication
    async for message in channel.history(limit=1000):  # Adjust the limit as needed
        if message.embeds:
            for embed in message.embeds:
                if embed.title == "Strike Logged":
                    user_field = next((field for field in embed.fields if field.name == "User"), None)
                    strikes_field = next((field for field in embed.fields if field.name == "Total Strikes"), None)
                    
                    if user_field and strikes_field:
                        user_mention = user_field.value
                        try:
                            user_id_str = ''.join(filter(str.isdigit, user_mention))
                            user_id = int(user_id_str)
                            strike_count = int(strikes_field.value)
                            strikes[user_id] = strike_count
                        except ValueError:
                            print(f"Failed to parse strike information from message ID {message.id}")

# Event handler for when the bot is ready
@bot.event
async def on_ready():
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    
    if log_channel is None:
        print(f"Log channel with ID {LOG_CHANNEL_ID} not found. Please check the channel ID.")
        return
    
    # Load members into a dictionary
    for guild in bot.guilds:
        for member in guild.members:
            members[member.name.lower()] = member
            members[member.display_name.lower()] = member
    
    await load_strikes_from_logs(log_channel)
    
    print(f'{bot.user} is connected to Discord!')
    print('Current strike information:')
    if strikes:
        for user_id, count in strikes.items():
            user = await bot.fetch_user(user_id)
            user_name = user.name if user else f"User ID {user_id}"
            print(f'{user_name}: {count} strike(s)')
    else:
        print('No strikes recorded.')

# Command that responds with hello
@bot.command(name='hello', help='Responds with hello')
async def hello(ctx):
    response = "Hello!"
    await ctx.send(response)

# Simplified command to add a strike to a user
@bot.command(name='strike', help='Adds a strike to a user. Usage: !strike username')
async def strike(ctx, user_input: str):
    user_input_lower = user_input.lower()

    # Find the user in the preloaded members dictionary
    user = members.get(user_input_lower)

    # If the user isn't found, send an error message
    if not user:
        await ctx.send(f"User '{user_input}' not found. Please make sure you spelled the name correctly.")
        return

    user_id = user.id
    if user_id in strikes:
        strikes[user_id] += 1
    else:
        strikes[user_id] = 1
    
    # Create the embed for the strike message
    embed = discord.Embed(title="Strike Issued", color=discord.Color.orange())
    embed.add_field(name="User", value=user.mention, inline=True)
    embed.add_field(name="Total Strikes", value=str(strikes[user_id]), inline=True)
    
    # Send the embed in the current channel
    await ctx.send(embed=embed)
    
    # Log the strike to the log channel
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_strike(user, strikes[user_id], log_channel)
    else:
        print(f"Log channel with ID {LOG_CHANNEL_ID} not found. Cannot log strike.")

# Command to delete all messages in the current channel
@bot.command(name='nuke', help='Deletes all messages in the current channel.')
@commands.has_permissions(manage_messages=True)
async def nuke(ctx):
    await ctx.channel.purge()
    confirmation_message = await ctx.send("Channel nuked! 💣")
    await confirmation_message.delete(delay=5)  # Delete the confirmation message after 5 seconds

# Command to repeat a user's message as an embed with the author's name and avatar
@bot.command(name='say', help='Repeats your input as an embed. Usage: !say your message here')
async def say(ctx, *, message: str):
    embed = discord.Embed(description=message, color=discord.Color.blue())
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    await ctx.send(embed=embed)

# Command to repeat a user's message as an embed without any author information
@bot.command(name='sayraw', help='Repeats your input as a raw embed. Usage: !sayraw your message here')
async def sayraw(ctx, *, message: str):
    embed = discord.Embed(description=message, color=discord.Color.green())
    await ctx.send(embed=embed)

# Run the bot with the token
if TOKEN:
    bot.run(TOKEN)
else:
    print("DISCORD_TOKEN not found in the environment variables.")
