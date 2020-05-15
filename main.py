import discord, logging, os, sqlite3, random, asyncio, math, psutil, platform
from discord.ext import commands, tasks
from itertools import cycle
from datetime import datetime
from time import sleep
from humanfriendly import format_timespan
from collections import Counter

userDB = sqlite3.connect("games.db")
userCursor = userDB.cursor()

prefix = "w."
client = commands.AutoShardedBot(command_prefix = commands.when_mentioned_or(prefix))
logger = logging.getLogger("discord")
logger.setLevel(logging.WARN)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
client.remove_command("help")
currentFolder = os.path.dirname(os.path.realpath(__file__))
TOKEN = open("bot.token").read()
client = commands.AutoShardedBot(command_prefix=commands.when_mentioned_or(prefix))
pythonProcess = psutil.Process(os.getpid())
client.remove_command("help")

wwRoles = ["werewolf","seer","gunner","doctor","alpha","aura","bodyguard","doctor","wseer","medium","shaman","jailer","priest","hh","villager","villager"]

@client.event
async def on_ready():
    change_status.start()
    log_bot_stats.start()
    print(f'Logged in as: {client.user.name}')
    print(f'With ID: {client.user.id}')

@tasks.loop(seconds=30)
async def change_status():
    status = cycle([f"Werewolf games with {len(client.users)} users!",f"Werewolf games in {len(client.guilds)} servers!"])
    await client.change_presence(activity=discord.Game(next(status)))

@tasks.loop(hours=4)
async def log_bot_stats():
    with open("bot.stats","a") as stats:
        currentTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        def get_size(bytes):
            for unit in ['', 'K', 'M', 'G', 'T', 'P']:
                if bytes < 1024:
                    return f"{bytes:.2f}{unit}B"
                bytes /= 1024
        systemInfo = []
        systemInfo.append(f"[{currentTime}]")
        systemInfo.append("="*40 + " System Information " + "="*40)
        uname = platform.uname()
        systemInfo.append(f"System: {uname.system}")
        systemInfo.append(f"Node Name: {uname.node}")
        systemInfo.append(f"Release: {uname.release}")
        systemInfo.append(f"Version: {uname.version}")
        systemInfo.append(f"Machine: {uname.machine}")
        systemInfo.append(f"Processor: {uname.processor}")
        systemInfo.append("="*40 + " CPU Info " + "="*40)
        systemInfo.append(f"Physical cores: {psutil.cpu_count(logical=False)}")
        systemInfo.append(f"Total cores: {psutil.cpu_count(logical=True)}")
        cpufreq = psutil.cpu_freq()
        systemInfo.append(f"Max Frequency: {cpufreq.max:.2f}Mhz")
        systemInfo.append(f"Min Frequency: {cpufreq.min:.2f}Mhz")
        systemInfo.append(f"Current Frequency: {cpufreq.current:.2f}Mhz")
        systemInfo.append("CPU Usage Per Core:")
        for i, percentage in enumerate(psutil.cpu_percent(percpu=True, interval=1)):
            systemInfo.append(f"Core {i}: {percentage}%")
        systemInfo.append(f"Total CPU Usage: {psutil.cpu_percent()}%")
        systemInfo.append("="*40 + " Memory Information " + "="*40)
        svmem = psutil.virtual_memory()
        systemInfo.append(f"Total: {get_size(svmem.total)}")
        systemInfo.append(f"Available: {get_size(svmem.available)}")
        systemInfo.append(f"Used: {get_size(svmem.used)}")
        systemInfo.append(f"Percentage: {svmem.percent}%")
        for stat in systemInfo:
            stats.write(f"{stat}\n")
        stats.write("\n\n")

@client.command()
async def botinfo(ctx):
    def get_size(bytes):
        for unit in ['', 'K', 'M', 'G', 'T', 'P']:
            if bytes < 1024:
                return f"{bytes:.2f}{unit}B"
            bytes /= 1024
    appInfo = await client.application_info()
    cpuUsage = psutil.cpu_percent()
    memUsage = get_size(pythonProcess.memory_full_info().uss)
    await ctx.send(f"Bot Info:\nBot Name: {appInfo.name}\nBot Owner: {appInfo.owner}\nBot Description: {appInfo.description}\nGuilds: {len(client.guilds)}\nUsers: {len(client.users)}\nCPU Usage: {cpuUsage}%\nMemory Usage: {memUsage}")

@client.command()
async def ping(ctx):
    await ctx.send("yes")
    await ctx.send(f'Current Ping: {round(client.latency*1000)}ms.')

@client.command()
async def help(ctx):
    commands={}
    commands["help"]="Shows this message"
    commands["botinfo"]="Sends information about the bot and server."
    commands["ping"]="Shows current bot ping."
    msg=discord.Embed(title='Wolfie Help', description="Written by JezzaR The Protogen#6483 using Discord.py",color=0x00ff99)
    for command,description in commands.items():
        msg.add_field(name=command,value=description)
    await ctx.send("", embed=msg)

@client.command()
async def create(ctx, *mode):
    try:
        mode = mode[0]
    except IndexError:
        await ctx.send("You need to say what gamemode you would like! (Werewolve/Mafia)")
        return
    mode = mode.lower()
    if mode != "werewolf" and mode != "mafia":
        await ctx.send("That is not a supported game type. (Check you've spelt it correctly!)")
        return
    userCursor.execute("SELECT * FROM games WHERE channelID = ?",(ctx.channel.id,))
    alreadyExists = userCursor.fetchall()
    try:
        alreadyExists = alreadyExists[0]
        noGame = False
    except IndexError:
        noGame = True
    if noGame:
        players = f"{ctx.author.id}"
        playerRoles = ""
        userCursor.execute("INSERT INTO games(channelID, initiatorID, gameMode, playing, players, playerRoles, playerVotes) VALUES(?,?,?,?,?,?,?)",(ctx.channel.id,ctx.author.id,mode,int(0),players,playerRoles,""))
        userDB.commit()
        await ctx.send(f"A game of `{mode.capitalize()}` has started in this channel! Use `w.join` to join it!")
    else:
        await ctx.message.delete()
        await ctx.author.send("You can only have one game going on in one channel at a time! Please wait for this game to finish.")

@client.command()
async def join(ctx):
    userCursor.execute("SELECT players FROM games WHERE channelID = ?",(ctx.channel.id,))
    currentPlayers = userCursor.fetchall()
    if currentPlayers == []:
        await ctx.send("There is no game going on in this channel!")
        return
    currentPlayers = currentPlayers[0][0].split(",")
    x = 0
    while x < len(currentPlayers):
        currentPlayers[x] = str(currentPlayers[x])
        x += 1
    if str(ctx.author.id) in currentPlayers:
        await ctx.send("You are already in this game!")
        return
    currentPlayers.append(str(ctx.author.id))
    currentPlayer = ",".join(currentPlayers)
    userCursor.execute("UPDATE games SET players = ? WHERE channelID = ?",(currentPlayer,ctx.channel.id))
    userDB.commit()
    userCursor.execute("SELECT gameMode FROM games WHERE channelID = ?",(ctx.channel.id,))
    gameMode = userCursor.fetchall()[0][0]
    await ctx.send(f"You have joined the `{gameMode.capitalize()}` game in this channel!")

@client.command()
async def start(ctx):
    global votingMessage
    userCursor.execute("SELECT players,channelID FROM games WHERE initiatorID = ?",(ctx.author.id,))
    try:
        players = userCursor.fetchall()[0]
    except IndexError:
        await ctx.send("You did not create the game on this channel so you can't start it!")
        return
    channelID = players[1]
    currentPlayers = players[0].split(",")
    if str(channelID) != str(ctx.channel.id):
        await ctx.send("You did not create the game on this channel so you can't start it!")
        return
    userCursor.execute("SELECT playing FROM games WHERE initiatorID = ?",(ctx.author.id,))
    playing = userCursor.fetchall()[0][0]
    if playing == 1:
        await ctx.send("The game is still going on! You cannot start it again.")
        return
    ''' if len(currentPlayers) < 4:
        await ctx.send(f"There aren't enough players to start! There are only {len(currentPlayers)} players out of the needed 4!")
        return '''
    userCursor.execute("SELECT gameMode FROM games WHERE channelID = ?",(ctx.channel.id,))
    gameMode = userCursor.fetchall()[0][0]
    if gameMode == "mafia":
        await ctx.send("Mafia games are currently unavaliable. You cannot start them.")
        return
    playerCount = 0
    currentGameRoles = []
    wwGameRoles = wwRoles[:len(currentPlayers)]
    while playerCount < len(currentPlayers):
        newRole = random.choice(wwGameRoles)
        currentGameRoles.append(newRole)
        wwGameRoles.remove(newRole)
        playerCount += 1
    playerRoleDict = {}
    playerCount = 0
    dots = "."
    message = await ctx.send(f"Assigning roles{dots}")
    for playerID in currentPlayers:
        guildObj = ctx.guild
        memberObject = guildObj.get_member(int(playerID))
        if memberObject == None:
            await ctx.send("There was an error getting User Objects from Discord. Cancelling Command.")
        playerRoleDict[playerID] = currentGameRoles[playerCount]
        await memberObject.send(f"You have been assigned the role of {currentGameRoles[playerCount].capitalize()}.")
        playerCount += 1
        dots += "."
        await message.edit(content=f"Assigning roles{dots}")
    userCursor.execute("UPDATE games SET playerRoles = ? WHERE initiatorID = ?",(",".join(currentGameRoles),ctx.author.id))
    userCursor.execute("UPDATE games SET playing = ? WHERE initiatorID = ?",(int(1),ctx.author.id))
    userDB.commit()
    playing = True
    while playing:
        await ctx.send("It is discussion time! You have 1 minute to throw around some random accusations!")
        await asyncio.sleep(60)
        votingMessage = await ctx.send("Now vote! Use `w.vote @player` to vote and `w.unvote` to remove your vote. You have 30 seconds! This message will be updated with the current votes.")
        await asyncio.sleep(30)
        userCursor.execute("SELECT playerVotes FROM games WHERE channelID = ?",(ctx.channel.id,))
        votes = userCursor.fetchall()[0][0]
        playerVote = Counter(votes.split(","))
        maxVotes = 0
        for playerID in players:
            memberObject = guildObj.get_member(int(playerID))
            name = memberObject.name.split("#")[0]
            playersVotes = playerVote[str(playerID)]
            if playersVotes > maxVotes:
                maxVotes = f"{name},{playersVotes}"
            elif playersVotes == maxVotes:
                maxVotes = "Draw"
                break
        userCursor.execute("SELECT players FROM games WHERE channelID = ?",(ctx.channel.id,))
        players = userCursor.fetchall()[0][0]
        players = players.split(",")
        if maxVotes == "Draw":
            await ctx.send("The village could not decide who to lynch.")
        elif maxVotes < math.floor(len(players)/2):
            await ctx.send("There were not enough votes to decisively lynch someone.")
        else:
            killed = maxVotes.split(",")
            toKill = killed[0]
            votes = killed[1]
            userCursor.execute("SELECT playerRoles FROM games WHERE channelID = ?",(ctx.channel.id,))
            roles = userCursor.fetchall()[0][0]
            roles = roles.split(",")
            count = 0
            role = None
            for ID in players:
                if str(ID) == str(roles[count]):
                    role = str(roles[count])
                    break
                else:
                    count += 1
            await ctx.send(f"{toKill} was lynched by the village with {votes} votes! They were {role}.")

@client.command()
async def vote(ctx, *member: discord.Member):
    userCursor.execute("SELECT playing FROM games WHERE channelID = ?",(ctx.channel.id,))
    playing = userCursor.fetchall()[0][0]
    if playing == 0:
        await ctx.send("There is no game going on in this channel!")
        return
    if member == []:
        await ctx.send("You need to mention who you want to vote for.")
        return
    member = member[0]
    userCursor.execute("SELECT players FROM games WHERE channelID = ?",(ctx.channel.id,))
    players = userCursor.fetchall()[0][0]
    players = players.split(",")
    if str(member.id) not in players:
        await ctx.send("That person isn't in this game!")
        return
    userCursor.execute("SELECT playerVotes FROM games WHERE channelID = ?",(ctx.channel.id,))
    votes = userCursor.fetchall()[0][0]
    try:
        votes = votes.split(",")
    except:
        votes = []
    while len(votes) < len(players):
        votes.append("")
    finalVotes = []
    count = 0
    for playerID in players:
        if playerID == str(ctx.author.id):
            finalVotes.append(str(member.id))
        else:
            finalVotes.append(str(votes[count]))
        count += 1
    finalVotes = ",".join(finalVotes)
    userCursor.execute("UPDATE games SET playerVotes = ? WHERE channelID = ?",(finalVotes,ctx.channel.id))
    userDB.commit()
    author = ctx.author.name
    mentioned = member.name
    await ctx.send(f"`{author.split('#')[0]}` has voted for `{mentioned.split('#')[0]}`")
    await ctx.message.delete()
    commands = {}
    embed = discord.Embed(title="Votes",description=f"Game in {ctx.channel}.")
    guildObj = ctx.guild
    playerVote = Counter(finalVotes.split(","))
    for playerID in players:
        memberObject = guildObj.get_member(int(playerID))
        name = memberObject.name.split("#")[0]
        playersVotes = playerVote[str(playerID)]
        commands[name]=f"has `{playersVotes}` votes."
    for command,description in commands.items():
        embed.add_field(name=command,value=description,inline=False)
    await votingMessage.edit(content="",embed=embed)

@client.command()
async def unvote(ctx):
    userCursor.execute("SELECT playing FROM games WHERE channelID = ?",(ctx.channel.id,))
    playing = userCursor.fetchall()[0][0]
    if playing == 0:
        await ctx.send("There is no game going on in this channel!")
        return
    userCursor.execute("SELECT playerVotes FROM games WHERE channelID = ?",(ctx.channel.id,))
    votes = userCursor.fetchall()[0][0]
    votes = votes.split(",")
    userCursor.execute("SELECT players FROM games WHERE channelID = ?",(ctx.channel.id,))
    players = userCursor.fetchall()[0][0]
    players = players.split(",")
    finalVotes = []
    count = 0
    for playerID in players:
        if playerID == str(ctx.author.id):
            finalVotes.append("")
            memberID = votes[count]
        else:
            finalVotes.append(str(votes[count]))
        count += 1
    finalVotes = ",".join(finalVotes)
    userCursor.execute("UPDATE games SET playerVotes = ? WHERE channelID = ?",(finalVotes,ctx.channel.id))
    userDB.commit()
    author = ctx.author.name
    guildObj = ctx.guild
    mentioned = guildObj.get_member(int(memberID))
    mentioned = mentioned.name
    await ctx.send(f"`{author.split('#')[0]}` has removed their vote for `{mentioned.split('#')[0]}`")
    await ctx.message.delete()
    commands = {}
    embed = discord.Embed(title="Votes",description=f"Game in {ctx.channel}.")
    counter = Counter(finalVotes.split(","))
    for playerID in players:
        memberObject = guildObj.get_member(int(playerID))
        name = memberObject.name.split("#")[0]
        playerVote = counter[str(playerID)]
        commands[name]=f"has `{playerVote}` votes."
    for command,description in commands.items():
        embed.add_field(name=command,value=description,inline=False)
    await votingMessage.edit(content="",embed=embed)

@client.event
async def on_guild_join(guild):
    channels = guild.text_channels
    for channel in channels:
        try:
            await channel.send("Thanks for adding me! I am Wolfie, a bot made so you can play Werewolf or Mafia games in your Discord server!\nMy default prefix is `w.` so you can use that or just mention me!\nGet started by using w.help to see all of my commands!")
            return
        except discord.errors.Forbidden:
            continue
    guildOwner = guild.owner
    await guildOwner.send(f"Hey there! I can't send messages to any of the channels in your server `{guild.name}`! This means I cannot work on your server, please fix this!")

'''@client.event
async def on_command_error(ctx, error):
    ignored = (commands.CommandNotFound, commands.UserInputError)
    if hasattr(ctx.command,"on_error"):
        return
    error = getattr(error, 'original', error)
    if isinstance(error, ignored):
        return
    elif isinstance(error, commands.CommandOnCooldown):
        seconds = math.ceil(error.retry_after)
        towait = format_timespan(seconds)
        return await ctx.send(f"Woah woah, slow down there, you have to wait {towait} seconds to do this command again.")'''

client.run(TOKEN)