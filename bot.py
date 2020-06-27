#!/usr/bin/env python3
# bot.py

# --------------------- [ IMPORTS ] --------------------- #
import os
import sys
import json
import signal
import discord
from datetime import datetime
from dotenv import load_dotenv
# ------------------------------------------------------- #

# ----------------- [ INITIALISATIONS ] ----------------- #
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
client = discord.Client()
# ------------------------------------------------------- #

# -------------------- [ FUNCTIONS ] -------------------- #
def write_log(msg, log_type="info"):
    """Custom log function"""
    if log_type == "info":
        prompt = "[-]"
    elif log_type == "warn":
        prompt = "[!]"
    elif log_type == "error":
        prompt = "[x]"
    else:
        prompt = "[~]"

    fmt_msg   = "[{0}] {1} {2}"
    timestamp = datetime.now().strftime("%H:%M:%S.%f")
    print(fmt_msg.format(timestamp, prompt, msg))

def activity_eq_overload(self, other):
    """Overload for discord.Activity '==' operator"""
    return self.name == other.name

def exit_gracefully(signum, frame):
    """Wait for bot to disconnect first when exitting"""
    signal.signal(signal.SIGINT, original_sigint)
    write_loge("Disconnecting...")
    client.close()
    sys.exit(0)

def is_playing_new_game(before, after):
    """
    Description:
        Checks whether a member has started playing a new game

    Args:
        before: The discord.Member object of the user's previous state
        after: The discord.Member object of the user's new state
    
    Returns:
        new_game: The discord.Game object of the new game if a user is playing one
        None: If the user isn't playing a new game
    """
    # Only get the difference in activities
    dif = [x for x in after.activities if x not in before.activities]

    # Only get the ones related to playing a game
    new_games = [x for x in dif if x.type == discord.ActivityType.playing]

    if new_games is not None and len(new_games) > 0:
        output = "{0} is now playing {1}".format(after.name, new_games[0].name)
        return new_games[0]
    else:
        return None

def get_friends_playing(game, server):
    """
    Description:
        Find users in a server that are playing a specified game

    Args:
        game: discord.Game object to search for
        server: discord.Guild object to search in

    Returns:
        friends_playing: Array of discord.Member objects
    """
    friends_playing = []

    for member in server.members:
        match = next((x for x in member.activities if x == game), None)
        if match is not None:
            friends_playing.append(member)

    return friends_playing

def get_active_games(server):
    """"
    Description:
        Returns a list of games users in a server a currently playing

    Args:
        server: discord.Guild object to search in

    Returns:
        A list of dictionaries in the format:
        {
            "game": discord.Game
            "players": [discord.Member]
        }    
    """

    games = []

    # First, collect all videos games being played
    for member in server.members:

        # Ignore bot accounts
        if member.bot: continue

        # List of games the member is playing
        playing = [x for x in member.activities if x.type == discord.ActivityType.playing]

        for game in playing:
            
            # List of all games currently collected
            all_games = [x["game"] for x in games]
            
            if game not in all_games:
                new_game = {
                    "game": game,
                    "players": []
                }
                games.append(new_game)

    for game in games:
        players = get_friends_playing(game["game"], server)
        game.update({"players": players})

    return games

# ------------------ [ EVENT HANDLERS ] ----------------- #
@client.event
async def on_ready():
    write_log(f'joined server as {client.user}')

@client.event
async def on_member_update(before, after):

    if len(after.activities) < 1:
        return

    new_game = is_playing_new_game(before, after)
    if new_game is not None:

        # If member is playing a new game

        # Send announcement message
        output = "{0} is now playing {1}".format(after.display_name, new_game.name)

        # Get announcement channel
        announce_chnl = next((x for x in after.guild.channels if x.name == "testing"), None)
        if announce_chnl is None:
            write_log("Couldn't find announcement channel!", log_type="error")
        else:
            await announce_chnl.send(content=output)

        # Check if other members in the server are also playing that game
        friends_playing = get_friends_playing(new_game, server=after.guild)

        # If other friends are playing
        if len(friends_playing) > 0:

            # Send direct message to member
            dm = f"Friends also playing {new_game.name}"
            for friend in friends_playing:
                # If returned member is current user, ignore
                if friend != after:
                    dm += f"\n - {friend.display_name}"
    
            if dm.count('\n') >= 1:
                await after.send(dm)

@client.event
async def on_message(message):

    # Ignore messages from self
    if message.author == client.user:
        write_log(message.content)
        return

    # Process commands
    if "who on?" == message.content.lower():

        write_log(f"{message.author} says: {message.content}")

        # Send a list of all games members are playing
        games = get_active_games(message.guild)
        if len(games) < 1: return

        # Craft message
        msg = ""
        for game in games:
            msg += "\n{0}:".format(game["game"].name)
            for player in game["players"]:
                msg += "\n\t - {0}".format(player.display_name)

        await message.channel.send(msg)

# ------------------------------------------------------- #

# -------------------- [ MAIN LOGIC ] ------------------- #
if __name__ == "__main__":
    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, exit_gracefully)
    setattr(discord.Activity, "__eq__", activity_eq_overload)
    client.run(TOKEN)
# ------------------------------------------------------- #