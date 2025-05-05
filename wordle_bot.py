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

IDS_HANDLES = {id : handle for handle, id in HANDLES_IDS.items()}

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
    first_line = message.strip().splitlines()[0]
    regex = r"Wordle \d{1,3}(?:,\d{3})* [1-6X]/6"
    return re.search(regex, first_line) is not None

def find_score(message):
    first_line = message.strip().splitlines()[0]
    regex = r"Wordle \d{1,3}(?:,\d{3})* ([1-6X])/6"
    match = re.search(regex, first_line)
    if match:
        score_str = match.group(1)
        return 7 if score_str == 'X' else int(score_str)
    return None

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    scan_channel.start()
DEBUG_MODE = True
DEBUG_NOW = datetime(2025, 5, 5, 18, 0, 0)

def get_expected_wordle_number(current_dt: datetime) -> str:
    days_since = (current_dt - FIRST_WORDLE_DATE).days
    raw_str = str(days_since)
    return f"{raw_str[0]},{raw_str[1:]}" if len(raw_str) > 1 else raw_str

def get_player_from_id(author_id):
    handle = IDS_HANDLES.get(author_id)
    return HANDLES_NAMES.get(handle)

@tasks.loop(time=times)
async def scan_channel():
    now = DEBUG_NOW if DEBUG_MODE else datetime.now(ZoneInfo("America/Los_Angeles"))
    print(f"[DEBUG] Now = {now}")

    expected_wordle_number = get_expected_wordle_number(now)
    print(f"[DEBUG] Expected Wordle #: {expected_wordle_number}")

    everyone_submitted = False
    messages = []
    daily_scores = {name: -1 for name in NAMES_HANDLES.keys()}

    await bot.wait_until_ready()
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if not channel:
        print("[ERROR] Channel not found.")
        return

    # Set PST range and convert to UTC
    tz = ZoneInfo("America/Los_Angeles")
    today_pst = now.astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_pst = today_pst - timedelta(days=1)
    tomorrow_pst = today_pst + timedelta(days=1)

    yesterday_utc = yesterday_pst.astimezone(ZoneInfo("UTC"))
    tomorrow_utc = tomorrow_pst.astimezone(ZoneInfo("UTC"))

    print(f"[DEBUG] Scanning messages between {yesterday_utc} and {tomorrow_utc} (PST window)")

    # --- Collect Valid Messages ---
    async for msg in channel.history(after=today_pst, before=tomorrow_pst):
        local_time = msg.created_at.astimezone(tz)

        if check_format(msg.content):
            print(f"[MSG] From {msg.author.name} at {local_time}: {msg.content.strip().splitlines()[0]}")
            messages.append({
                "author": msg.author.name,
                "author_id": msg.author.id,
                "score": find_score(msg.content),
                "timestamp": msg.created_at
            })

    # --- Assign Scores from Messages ---
    for msg in messages:
        player = get_player_from_id(msg["author_id"])
        if player and msg["score"] is not None:
            daily_scores[player] = msg["score"]

    # --- Retroactive Scan for Missing Players ---
    for player, score in daily_scores.items():
        if score != -1:
            continue
        print(f"[DEBUG] Retroactively scanning for {player}...")

        async for msg in channel.history(after=yesterday_pst, before=today_pst):
            if (
                msg.author.id in HANDLES_IDS.values()
                and check_format(msg.content)
                and expected_wordle_number in msg.content
            ):
                author = get_player_from_id(msg.author.id)
                if author == player:
                    score = find_score(msg.content)
                    if score is not None:
                        daily_scores[author] = score
                        print(f"[DEBUG] Found retroactive score for {author}: {score}")
                        break

    # --- Reminders or Defaults ---
    if now.hour == 18:
        missing = [f"<@{HANDLES_IDS[NAMES_HANDLES[p]]}>" for p, score in daily_scores.items() if score == -1]
        if missing:
            await channel.send(f"{' '.join(missing)} — submit your Wordle")
        else:
            await channel.send("✅ Everyone has submitted by the midway point!")
            everyone_submitted = True

    elif now.hour == 23:
        for player in daily_scores:
            if daily_scores[player] == -1:
                daily_scores[player] = 7
        everyone_submitted = True

    # --- Save Scores ---
    today_str = f"{now.month}/{now.day}/{now.year}"
    cleaned_scores = {k: (7 if v == -1 else v) for k, v in daily_scores.items()}
    history[today_str] = pd.Series(cleaned_scores)

    print("[scan_channel] Final scores to save:", cleaned_scores)

    if everyone_submitted:
        message = "Here's how everyone did today:\n"
        for name, score in cleaned_scores.items():
            message += f"{name}: {score}\n"
        await channel.send(f"```{message}```")

    save_data(history, HISTORY_PATH.split('.')[0])

@bot.command()
async def find_user(ctx, user_id: int):
    channel = ctx.channel  # Or use bot.get_channel(CHANNEL_ID)

    async for message in channel.history(limit=None):
        if message.author.id == user_id:
            await ctx.send(f"✅ Found user <@{user_id}>. First message:\n```{message.content}```")
            return

    await ctx.send(f"❌ No messages found from user ID {user_id} in this channel.")

@bot.command()
async def manual_insert(ctx, score: int, date: str, player: str):
    if player not in NAMES_HANDLES.keys():
        await ctx.send(f"Invalid player {player}")
        return
    else:
        if date in history.columns:
            history.at[player, date] = score
        else:
            await ctx.send(f"Invalid Date {date}")
            return

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
    if time_frame is None or time_frame.lower() == 'alltime':
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
            await channel.send("Invalid week format. Please use `week<number>`.")
            return

        week_number = int(match.group(1))
        weeks_passed = int(math.ceil((date.today() - START_DATE.date()).days / 7) + 1)

        if week_number >= weeks_passed or week_number < 1:
            await channel.send("Invalid Week number.")
            return

        if week_number <= 4:
            base_date = START_DATE
            offset_weeks = week_number - 1
        else:
            base_date = SKIP_DATE + timedelta(days=1)
            offset_weeks = week_number - 5  # Since week 5 is the first week after skip

        query_start_dt = base_date + timedelta(weeks=offset_weeks)
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

@bot.command()
async def print_all_messages(ctx):
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if not channel:
        await ctx.send("Channel not found.")
        return

    tz = ZoneInfo("America/Los_Angeles")
    now = datetime.now(tz)

    # Midnight PST today and tomorrow
    today_pst = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_pst = today_pst + timedelta(days=1)

    # Convert to UTC for Discord API
    after_utc = today_pst.astimezone(ZoneInfo("UTC"))
    before_utc = tomorrow_pst.astimezone(ZoneInfo("UTC"))

    print(f"[DEBUG] Scanning from {after_utc} to {before_utc} (PST day)")

    count = 0
    async for msg in channel.history(after=after_utc, before=before_utc, oldest_first=True):
        local_time = msg.created_at.astimezone(tz)
        print(f"[{local_time.strftime('%Y-%m-%d %H:%M:%S %Z')}] {msg.author.name}: {msg.content.strip()}")
        count += 1

    await ctx.send(f"✅ Printed {count} messages from midnight to midnight PST.")


bot.run(TOKEN)

