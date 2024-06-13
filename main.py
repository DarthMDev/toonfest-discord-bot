# discord bot that will send a message every day on the reaming days till may 24th
# user will use a command to setup the channel it will send the message in
import io
import os
import datetime
import json 
import aiohttp
import asyncio 
import discord
from discord import app_commands
import pytz
from discord.ext import tasks 
from discord.ext import commands
import yt_dlp as youtube_dl 

# set the timezone to  Central Time
timezone = pytz.timezone('US/Central')
 # grab the token from config.json 
with open('config.json') as f:
    config = json.load(f)
    token = config['token']
global bot
intents = discord.Intents.default()
intents.message_content = True
guild_id = 1111422999741083710
channel_id = 1204161676522291261

bot =  commands.Bot(command_prefix='!', intents=intents)

def main():   
    bot.run(token)

# bot command to set the channel to send the message in , need to have the Admin role to use this command
@bot.hybrid_command(
    name='set_channel',
    description='Set the channel to send the message in',
    guild=discord.Object(id=guild_id)
)
async def set_channel(ctx, channel: discord.TextChannel):
    global channel_id
    if ctx.author.guild_permissions.manage_channels:
        channel_id = channel.id
        await ctx.send(f"Channel has been set to {channel.mention}")
    else:
        await ctx.send("You need to have the Manage Channels permission to use this command")

# set the status to the remaining time till toonfest in days 
async def set_status():
    remaining_days, _, _ = get_remaining_time()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"Toonfest's status: {remaining_days} days "))

@bot.event
async def on_ready():
    now = datetime.datetime.now(timezone)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
    remaining_time = (midnight - now).total_seconds()
    send_message.change_interval(seconds=remaining_time)
    send_message.start()
    await set_status()
    print("Bot is ready")

# send the message at 12 am est every day
@tasks.loop()
async def send_message():
    # if there is no existing message , send a new one
    # if not , edit the existing message
    await send_remaining_time(manual_override=False)
    await set_status()

# bot command to get the remaining time till may 24th
@bot.hybrid_command(
    name='remaining_time',
    description='Get the remaining time till toonfest',
    guild=discord.Object(id=guild_id)
)   
async def remaining_time(ctx):
    current_channel = ctx.channel
    await send_remaining_time(manual_override=True, channel=current_channel)
   
song_queue = []
async def play_from_queue(ctx):
    if not song_queue:
        return  # Exit if the queue is empty
    url = song_queue.pop(0)  # Get the first song in the queue
    # The rest of the code is similar to the play function, but adapted for queue playback
    if not ctx.guild.voice_client:
        player = await ctx.author.voice.channel.connect()
    else:
        player = ctx.guild.voice_client
    options = {
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }],
        "format": "bestaudio/best",
        "outtmpl": "yt_song"
    }
    with youtube_dl.YoutubeDL(options) as dl:
        dl.download([url])
    player.play(discord.FFmpegPCMAudio("yt_song.mp3"), after=lambda e: asyncio.run_coroutine_threadsafe(play_from_queue(ctx), ctx.bot.loop))
    title = dl.extract_info(url, download=False).get('title', None)
    await ctx.send(f"Playing: {title}")
    if os.path.exists('yt_song.mp3'):
        os.remove("yt_song.mp3")

# bot command to download and play music locally, supports youtube and local files
@bot.hybrid_command(
    name='play',
    description='Play music',
    guild=discord.Object(id=guild_id)
)


async def play(ctx, url: str):
    if ctx.author.voice.channel:
        if ctx.guild.voice_client and ctx.guild.voice_client.is_playing():
            song_queue.append(url)  # Add song to queue if something is already playing
           # tell the user what position the queue its in
            await ctx.send(f"Added to queue. Position: {len(song_queue)}")
        else:
            song_queue.append(url)  # Add to queue regardless, to simplify logic
            await ctx.send(f"Added to queue. Position: {len(song_queue)}")
            await play_from_queue(ctx)  # Start playing from queue immediately



# command to clear the song queue and leave the voice channel
@bot.hybrid_command(
    name='leave',
    description='Leave the voice channel',
    guild=discord.Object(id=guild_id)
)
async def leave(ctx):
    voice_channel = ctx.author.voice.channel
    if voice_channel:
        voice = ctx.guild.voice_client
        voice.stop()
        await voice.disconnect()
    else:
        await ctx.send("You need to be in a voice channel to use this command")


# command to pause the music
@bot.hybrid_command(
    name='pause',
    description='Pause the music',
    guild=discord.Object(id=guild_id)
)
async def pause(ctx):
    voice_channel = ctx.author.voice.channel
    if voice_channel:
       # assume bot is already in vc
        voice = ctx.guild.voice_client
        voice.pause()
    else:
        await ctx.send("You need to be in a voice channel to use this command")

# command to resume the music
@bot.hybrid_command(
    name='resume',
    description='Resume the music',
    guild=discord.Object(id=guild_id)
)
async def resume(ctx):
    voice_channel = ctx.author.voice.channel
    if voice_channel:
        voice = ctx.guild.voice_client
        voice.resume()
    else:
        await ctx.send("You need to be in a voice channel to use this command")



           
def get_remaining_time():
    # return the remaining days, hours and minutes till December 6th
    today = datetime.datetime.now()
    may_24 = datetime.datetime(2024, 12, 6, 12)
    
    remaining = may_24 - today
    return remaining.days, remaining.seconds // 3600, (remaining.seconds % 3600) // 60

async def send_remaining_time(manual_override=False, channel=None):
    remaining_days, remaining_hours, remaining_minutes = get_remaining_time()
    guild = bot.get_guild(guild_id)
    if not channel:
        channel = guild.get_channel(channel_id)
    if channel and manual_override:
        await channel.send(f"Remaining time till Toonfest: {remaining_days} days, {remaining_hours} hours, {remaining_minutes} minutes")
    elif not manual_override:
        await edit_remaining_time_message()
    else:
        print("Channel not found")
        return

async def edit_remaining_time_message():
    remaining_days, remaining_hours, remaining_minutes = get_remaining_time()
    guild = bot.get_guild(guild_id)
    channel = guild.get_channel(channel_id)
    async for message in channel.history(limit=200):
        if message.author == bot.user:
            await message.edit(content=f"Remaining time till Toonfest: {remaining_days} days, {remaining_hours} hours, {remaining_minutes} minutes")
            return
# bot command to get the current schedule image and send it to the channel message was sent
# in
@bot.hybrid_command(
    name='getschedule',
    description='Get the current schedule',
    guild=discord.Object(id=guild_id)
)
async def get_schedule(ctx):
    guild = bot.get_guild(guild_id)
    channel = ctx.channel
    await channel.send(file=discord.File('images/24-4-17_toonfest24schedule.png'))


@bot.tree.command(name='sync', description='Owner only')
async def sync(interaction: discord.Interaction):
    if interaction.user.id == 195297683907411970:
        await bot.tree.sync()
        print('Command tree synced.')
    else:
        await interaction.response.send_message('You must be the owner to use this command!')

@bot.command()
async def sync(ctx):
    print("sync command")
    if ctx.author.id == 195297683907411970:
        await bot.tree.sync()
        await ctx.send('Command tree synced.')
    else:
        await ctx.send('You must be the owner to use this command!')
if __name__ == "__main__":
    main()