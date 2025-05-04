import os
import pickle 
import discord
import re
import math
from discord.ext import tasks, commands
from dotenv import load_dotenv

import asyncio
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
from matplotlib import pyplot as plt

NAMES_HANDLES = {'Felix': 'aegislock', 
                 'Eden': 'gravity_chicken', 
                 'Jason': 'xownfos', 
                 'Jovia': 'min.wei', 
                 'Julina': 'julinaka08', 
                 'Justin': 'crypticlucid', 
                 'Renee': 'daydream9819'}

HANDLES_NAMES = {handle: name for name, handle in NAMES_HANDLES.items()}

HANDLES_IDS = {'aegislock': 665285104259825668,
               'gravity_chicken': 542537288048050176,
               'xownfos': 463471634787991552,
               'min.wei': 645475740560916531,
               'julinaka08': 786663830955491368,
               'crypticlucid': 661662934975512587,
               'daydream9819': 840813927297974272}

HISTORY_PATH = "C:\\Users\\tongf\\Wordle-Discord-Bot\\history.pkl"
TOKEN_PATH = "C:\\Users\\tongf\\Wordle-Discord-Bot\\token.pkl"
# Define midnight in PST

midway_point_pst = time(hour = 18, minute=0, second=0, tzinfo=ZoneInfo("America/Los_Angeles"))
midnight_pst = time(hour=23, minute=59, second=59, tzinfo=ZoneInfo("America/Los_Angeles"))
times = [midway_point_pst, midnight_pst]

FIRST_WORDLE_DATE = datetime(2021, 6, 19) #Math for calculating wordle #
START_DATE = datetime(2025, 3, 10) #Day 0
SKIP_DATE = datetime(2025, 4, 7) #Day we skipped between Month 1 and Month 2

# Load environment variables
load_dotenv()

TARGET_CHANNEL_ID = 1331497722544521238

intents = discord.Intents.default()
intents.messages = True  
intents.message_content = True
intents.guilds = True  

bot = commands.Bot(command_prefix='!', intents=intents)

def save_data(structure, name):
    # Save
    with open(f'{name}.pkl', 'wb') as f:
        pickle.dump(structure, f)

def load_data(file):
    with open(file, 'rb') as f:
        loaded_data = pickle.load(f)
        return loaded_data
    
history = load_data(HISTORY_PATH)
TOKEN = load_data(TOKEN_PATH)

def check_format(message):
    regex =  r"^Wordle \d{1,3}(,\d{3})? [1-6X]/6$"
    match = re.search(regex, message)
    if match is not None:
        return True
    return False

def find_score(message):
    regex = r"^Wordle \d{1,3}(,\d{3})? [1-6X]/6$"
    match = re.search(regex, message)
    if match is not None and match.group()[13] != 'X':
        return int(match.group()[13])
    elif match is not None:
        return 7
        
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@tasks.loop(time=times)
async def scan_channel():
    now = datetime.now(ZoneInfo("America/Los_Angeles")).time()
    expected_wordle_number = (datetime.now() - START_DATE).days

    messages = []
    daily_scores = {name: -1 for name in NAMES_HANDLES.keys()}

    await bot.wait_until_ready()
    channel = bot.get_channel(TARGET_CHANNEL_ID)


    today = datetime.combine(datetime.now().date(), time.min).replace(tzinfo=ZoneInfo("America/Los_Angeles"))
    yesterday = today - timedelta(days=1)

    if channel:
        async for current_message in message.channel.history(after=today):
            if check_format(current_message.content):
                messages.append({
                    "author": current_message.author.name,
                    "author_id": current_message.author.id,
                    "score": find_score(current_message.content),
                    "timestamp": str(current_message.created_at)
                })
    if messages:
        for message in messages:
            if message["author"] in NAMES_HANDLES:
                daily_scores[NAMES_HANDLES[message["author"]]] = message["score"]

        for player in daily_scores:
            if daily_scores[player] == -1:
                # Search for today's submission (in different timezone)
                if channel:
                    async for current_message in channel.history(after=yesterday, before=today):
                        if (
                            current_message.author.name in NAMES_HANDLES and
                            check_format(current_message.content) and
                            str(expected_wordle_number) in current_message.content
                        ):
                            daily_scores[NAMES_HANDLES[current_message.author.name]] = find_score(current_message.content)
        if now.hour == 18:
            if channel:
                missing_mentions = []

                for player in daily_scores:
                    if daily_scores[player] == -1 and player in NAME_TO_ID:
                        mention = f"<@{HANDLES_IDS[player]}>"
                        missing_mentions.append(mention)
                if missing_mentions:
                    mentions_text = ' '.join(missing_mentions)
                    await channel.send(f"{mentions_text} — submit your Wordle")
                else:
                    await channel.send("✅ Everyone has submitted by the midway point!")
    
        elif now.hour == 23:
            for player in daily_scores:
                if daily_scores[player] == -1:
                    daily_scores[player] = 7

        today = date.today().strftime("%-m/%-d/%Y")
        history[today] = pd.Series(daily_scores).fillna(7)

        save_data(history, HISTORY_PATH.split('.')[0])
    else:
        if channel:
            await channel.send("No messages from today to save.")

@bot.command()
async def leaderboard(ctx, time_frame: str = None):
    import re
    import math
    from datetime import date, datetime, timedelta

    channel = bot.get_channel(TARGET_CHANNEL_ID)

    def calculate_points(df):
        score_df = pd.DataFrame(index=df.index)

        for col in df.columns:
            guesses = df[col]

            # Filter only completed (1–6)
            valid = guesses[guesses < 7].dropna()

            # Count frequency of guess values
            rank_order = sorted(valid.unique())
            player_scores = {}

            rank_scores = {1: 6, 2: 4, 3: 2}  # default scoring
            rank = 1

            for guess_val in rank_order:
                players = valid[valid == guess_val].index.tolist()
                score = rank_scores.get(rank, 1)  # 1 point if outside top 3
                for player in players:
                    player_scores[player] = score
                rank += 1

            # Fill in players who didn’t complete or guessed 7
            for player in guesses.index:
                if player not in player_scores:
                    player_scores[player] = 0

            score_df[col] = pd.Series(player_scores)

        return score_df

    # Convert guess data to points
    score_df = calculate_points(history)

    # -------- All-time leaderboard --------
    if time_frame is None or time_frame.lower() == 'all time':
        total_scores = score_df.sum(axis=1)
        sorted_scores = total_scores.sort_values(ascending=False)

        message = "**🏆 Total Wordle Scores Leaderboard**\n```"
        for rank, (name, score) in enumerate(sorted_scores.items(), 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank:>2}.")
            message += f"{medal} {name:<10} — {int(score):>3} pts\n"
        message += "```"

        if channel:
            await channel.send(message)
        return

    # -------- Weekly leaderboard --------
    if "week" in time_frame.lower():
        match = re.search(r"week\s*(\d+)", time_frame.lower())
        if not match:
            await channel.send("Invalid week format. Please use `week <number>`.")
            return

        week_number = int(match.group(1))
        weeks_passed = math.ceil((date.today() - START_DATE.date()).days / 7)

        if week_number >= weeks_passed or week_number < 1:
            await channel.send("Invalid Week number.")
            return

        base_date = START_DATE if week_number <= 4 else SKIP_DATE + timedelta(days=1)
        query_start_dt = base_date + timedelta(days=(week_number - (1 if base_date == START_DATE else 4)) * 7)
        query_end_dt = query_start_dt + timedelta(days=6)

        start_str = f"{query_start_dt.month}/{query_start_dt.day}/{query_start_dt.year}"
        end_str = f"{query_end_dt.month}/{query_end_dt.day}/{query_end_dt.year}"

        matching_columns = [
            col for col in score_df.columns
            if query_start_dt <= datetime.strptime(col, "%m/%d/%Y") <= query_end_dt
        ]

        if not matching_columns:
            await channel.send(f"No data found for Week {week_number}.")
            return

        week_df = score_df[matching_columns]
        total_scores = week_df.sum(axis=1)
        sorted_scores = total_scores.sort_values(ascending=False)

        message = f"**🏆 Week {week_number} Wordle Scores Leaderboard**\n({start_str} to {end_str})\n```"
        for rank, (name, score) in enumerate(sorted_scores.items(), 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank:>2}.")
            message += f"{medal} {name:<10} — {int(score):>3} pts\n"
        message += "```"

        await channel.send(message)
        return

    # -------- Fallback --------
    await channel.send("Invalid command usage. Try `!leaderboard`, `!leaderboard alltime`, or `!leaderboard week<number>`.")

bot.run(TOKEN)

