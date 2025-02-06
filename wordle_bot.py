# bot.py
import os
import json
import discord
from discord.ext import commands
from dotenv import load_dotenv

import asyncio
import time
from datetime import datetime


JSON_FILE = "data.json"

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Enable intents (default + message handling)
intents = discord.Intents.default()
intents.messages = True  # Allows handling message events
intents.message_content = True
intents.guilds = True  # Allows handling guild-related events

# Create the client with intents
client = discord.Client(intents=intents)

#active_channels = []

def load_data(filename):
    try:
        with open(filename, "r") as f:
            data = json.load(f)
        return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading {filename}: {e}")
        return []
    
# Sort messages by score
def sort_messages_by_score(filename):
    data = load_data(filename)

    # Ensure scores are treated as integers before sorting
    sorted_data = sorted(data, key=lambda x: int(x["score"]))

    return sorted_data

# Load existing messages from JSON file
# def load_messages():
#     try:
#         with open(JSON_FILE, "r") as f:
#             return json.load(f)
#     except (FileNotFoundError, json.JSONDecodeError):
#         return []
    
# Save messages to JSON file
# def save_messages(messages):
#     with open(JSON_FILE, "w") as f:
#         json.dump(messages, f, indent=4)

# checks if this is a wordle report
def check_format(message):
    if "Wordle " in message and message[8] == "," and message[7].isdigit() and message[13].isdigit() and len(message) > 13:
        return True
    else:
        return False

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    #client.loop.create_task(daily_leaderboard())  # Start the daily leaderboard task



@client.event
async def on_message(message):
    global active_channels

    if message.author == client.user:
        return
    
    # if message.content.startswith("Wordle "):
    #     if not check_format(message.content):
    #         return
    #     else:
    #         await message.channel.send("Stats saved!")
        
        # Store messages in a JSON file per channel
        # channel_id = str(message.channel.id)  # Get channel ID as string
        # filename = f"stats_{channel_id}.json"

        # # Load existing messages for this channel
        # if os.path.exists(filename):
        #     with open(filename, "r") as f:
        #         messages = json.load(f)
        # else:
        #     messages = []

        # # Append new message
        # messages.append({
        #     "author": message.author.name,
        #     "author_id": message.author.id,
        #     "score": message.content[13],
        #     "timestamp": str(message.created_at)
        # })

        # if (channel_id not in active_channels):
        #     active_channels.append(channel_id)

        # Save back to JSON file
        # with open(filename, "w") as f:
        #     json.dump(messages, f, indent=4)


    if message.content.startswith("!leaderboard"):
       
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)  # Midnight UTC

        messages = []
        filename = f"stats.json"

        async for current_message in message.channel.history(after=today):
            if current_message.created_at.date() == message.created_at.date() and check_format(current_message.content):  # Check if the message is from today
                messages.append({
                    "author": current_message.author.name,
                    "author_id": current_message.author.id,
                    "score": current_message.content[13],
                    "timestamp": str(current_message.created_at)
                })
        # Save messages to a JSON file for the channel
        if messages:
            with open(filename, "w") as f:
                json.dump(messages, f, indent=4)

            print(f"Saved {len(messages)} messages from today.")
        else:
            await message.channel.send("No messages from today to save.")

        if messages:
            sorted_messages = sort_messages_by_score(filename)

            count = 0
            previous_score = 0
            await message.channel.send("**Here's how everyone did today:**")
            for current_message in sorted_messages:
                if not current_message['score'] == previous_score:
                    count+=1
                    await message.channel.send("--------------------")
                    if count == 1:
                        emoji = "🥇"
                    elif count == 2:
                        emoji = "🥈"
                    elif count == 3:
                        emoji = "🥉"
                    else:
                        emoji = "🏅"
                    
                    await message.channel.send(f"{emoji}  {current_message['author']}'s score - {current_message['score']}")
                    previous_score = current_message['score']
                else:
                    await message.channel.send(f"{emoji}  {current_message['author']}'s score - {current_message['score']}")
                    previous_score = current_message['score']

            
        if os.path.exists(filename):
            os.remove(filename)
            print(f"File '{filename}' deleted successfully.")
        else:
            print(f"File '{filename}' not found.")
        

# async def daily_leaderboard():
#     global active_channels
#     await client.wait_until_ready()  # Ensure bot is ready before running
#     while not client.is_closed():
#         print(active_channels)
#         now = time.strftime("%H:%M")  # Get current time in HH:MM format
#         if now == "15:31":  # Run at specified server time
#             print("Running daily leaderboard!")
#             for channel_id in active_channels:
#                 channel = client.get_channel(int(channel_id))  # Get actual channel object
#                 if channel:
#                     await channel.send("📊 **Daily Leaderboard** coming soon!")
#         await asyncio.sleep(60)  # Check every minute

client.run(TOKEN)
