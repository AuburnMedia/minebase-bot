#!./bot-env/bin/python3

import os
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
from dotenv import load_dotenv

# Load the .env file that contains your token
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Set the log channel ID directly
LOG_CHANNEL_ID = 1271302668945719439  # Replace with your actual log channel ID

# Define intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.members = True  # Required to fetch member list
intents.reactions = True  # Required to handle reactions

# Create a bot instance with a command prefix and specified intents
bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionary to store strikes for each user by their user ID
strikes = {}
# Dictionary to store members by name for quick lookup
members = {}
# Dictionary to map message IDs to reaction-role configurations
reaction_roles = {}

# Sync the commands to Discord
@bot.event
async def on_ready():
    print(f'{bot.user} is connected to Discord!')
    # Load members into a dictionary
    for guild in bot.guilds:
        for member in guild.members:
            members[member.name.lower()] = member
            members[member.display_name.lower()] = member
    
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel is None:
        print(f"Log channel with ID {LOG_CHANNEL_ID} not found. Please check the channel ID.")
        return
    
    await load_strikes_from_logs(log_channel)
    
    print('Current strike information:')
    if strikes:
        for user_id, count in strikes.items():
            user = await bot.fetch_user(user_id)
            user_name = user.name if user else f"User ID {user_id}"
            print(f'{user_name}: {count} strike(s)')
    else:
        print('No strikes recorded.')
    
    # Sync the slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

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

# A view with buttons for confirming or canceling the strike
class ConfirmStrikeView(View):
    def __init__(self, user, strike_count, interaction):
        super().__init__()
        self.user = user
        self.strike_count = strike_count
        self.interaction = interaction

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == self.interaction.user:
            await interaction.response.defer()  # Acknowledge the button press
            strikes[self.user.id] = self.strike_count
            embed = discord.Embed(title="Strike Confirmed", color=discord.Color.orange())
            embed.add_field(name="User", value=self.user.mention, inline=True)
            embed.add_field(name="Total Strikes", value=str(self.strike_count), inline=True)
            # Send a public message confirming the strike
            await self.interaction.followup.send(embed=embed)
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                await log_strike(self.user, self.strike_count, log_channel)
        else:
            await interaction.response.send_message("You cannot confirm this strike.", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == self.interaction.user:
            await interaction.response.defer()  # Acknowledge the button press
            strikes[self.user.id] -= 1  # Remove the strike
            await interaction.followup.send(f"Strike on {self.user.mention} has been canceled.", ephemeral=True)
        else:
            await interaction.response.send_message("You cannot cancel this strike.", ephemeral=True)

# Slash command to add a strike to a user
@bot.tree.command(name='strike', description='Adds a strike to a user.')
@app_commands.describe(user='The user to strike')
async def strike(interaction: discord.Interaction, user: discord.Member):
    user_id = user.id
    if user_id in strikes:
        strikes[user_id] += 1
    else:
        strikes[user_id] = 1

    if strikes[user_id] == 3:
        # Create the embed for the confirmation
        embed = discord.Embed(title="Strike Confirmation", description=f"{user.mention} has reached 3 strikes. Continuing will punish the user. Confirm or cancel?", color=discord.Color.orange())
        view = ConfirmStrikeView(user, strikes[user_id], interaction)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        # Create the embed for the strike message
        embed = discord.Embed(title="Strike Issued", color=discord.Color.orange())
        embed.add_field(name="User", value=user.mention, inline=True)
        embed.add_field(name="Total Strikes", value=str(strikes[user_id]), inline=True)
        await interaction.response.send_message(embed=embed)

        # Log the strike to the log channel
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_strike(user, strikes[user_id], log_channel)
        else:
            print(f"Log channel with ID {LOG_CHANNEL_ID} not found. Cannot log strike.")

# Slash command to delete all messages in the current channel
@bot.tree.command(name='nuke', description='Deletes all messages in the current channel.')
@app_commands.checks.has_permissions(manage_messages=True)
async def nuke(interaction: discord.Interaction):
    await interaction.channel.purge()
    await interaction.response.send_message("Channel nuked! 💣", ephemeral=True)

# Slash command to repeat a user's message as an embed with the author's name and avatar
@bot.tree.command(name='say', description='Repeats your input as an embed.')
@app_commands.describe(message='The message to repeat')
async def say(interaction: discord.Interaction, message: str):
    embed = discord.Embed(description=message, color=discord.Color.blue())
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    await interaction.response.send_message(embed=embed)

# Slash command to repeat a user's message as an embed without any author information
@bot.tree.command(name='sayraw', description='Repeats your input as a raw embed.')
@app_commands.describe(message='The message to repeat')
async def sayraw(interaction: discord.Interaction, message: str):
    embed = discord.Embed(description=message, color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

# Slash command to set up reaction roles
@bot.tree.command(name='setupreactionroles', description='Set up reaction roles with emojis and roles.')
@app_commands.describe(
    emoji1='First emoji', role1='First role',
    emoji2='Second emoji', role2='Second role',
    emoji3='Third emoji', role3='Third role',
    emoji4='Fourth emoji', role4='Fourth role',
    emoji5='Fifth emoji', role5='Fifth role',
    emoji6='Sixth emoji', role6='Sixth role',
    emoji7='Seventh emoji', role7='Seventh role'
)
async def setupreactionroles(interaction: discord.Interaction,
                             emoji1: str, role1: discord.Role,
                             emoji2: str = None, role2: discord.Role = None,
                             emoji3: str = None, role3: discord.Role = None,
                             emoji4: str = None, role4: discord.Role = None,
                             emoji5: str = None, role5: discord.Role = None,
                             emoji6: str = None, role6: discord.Role = None,
                             emoji7: str = None, role7: discord.Role = None):
    # Create a list of tuples (emoji, role) based on the provided arguments
    roles = [(emoji1, role1), (emoji2, role2), (emoji3, role3), (emoji4, role4), 
             (emoji5, role5), (emoji6, role6), (emoji7, role7)]
    
    # Filter out the None values
    roles = [(emoji, role) for emoji, role in roles if emoji and role]

    # Build the embed message
    embed = discord.Embed(title="Reaction Roles", description="React with the corresponding emoji to get the role", color=discord.Color.blue())
    for emoji, role in roles:
        embed.add_field(name=f"{emoji}", value=f"{role.mention}", inline=False)

    # Send the embed message
    message = await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()  # Fetch the original message
    
    # Add reactions to the message and update the reaction_roles dictionary
    for emoji, role in roles:
        try:
            await message.add_reaction(emoji)
            # Map the message ID to the role configuration
            if message.id not in reaction_roles:
                reaction_roles[message.id] = {}
            reaction_roles[message.id][emoji] = role
        except discord.HTTPException:
            await interaction.followup.send(f"Failed to add reaction: {emoji}", ephemeral=True)

# Event listener for on_reaction_add
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return  # Ignore reactions from bots
    
    # Check if the reaction is in the reaction_roles mapping
    if reaction.message.id in reaction_roles:
        role = reaction_roles[reaction.message.id].get(str(reaction.emoji))
        if role:
            try:
                await user.add_roles(role)
                await reaction.message.channel.send(f"Added {role.mention} to {user.mention}", delete_after=5)
            except discord.Forbidden:
                print(f"Missing permissions to add role {role.name} to {user.name}")

# Event listener for on_reaction_remove
@bot.event
async def on_reaction_remove(reaction, user):
    if user.bot:
        return  # Ignore reactions from bots
    
    # Check if the reaction is in the reaction_roles mapping
    if reaction.message.id in reaction_roles:
        role = reaction_roles[reaction.message.id].get(str(reaction.emoji))
        if role:
            try:
                await user.remove_roles(role)
                await reaction.message.channel.send(f"Removed {role.mention} from {user.mention}", delete_after=5)
            except discord.Forbidden:
                print(f"Missing permissions to remove role {role.name} from {user.name}")

# Run the bot with the token
if TOKEN:
    bot.run(TOKEN)
else:
    print("DISCORD_TOKEN not found in the environment variables.")
