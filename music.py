import asyncio
import datetime
import json
from random import shuffle
import discord
import spotipy
from discord import FFmpegOpusAudio, VoiceClient, Embed, Message
from discord.ext.commands import Cog
from discord_slash import cog_ext, SlashContext, ComponentContext, ButtonStyle
from discord_slash.utils.manage_components import create_button, create_select, create_select_option, create_actionrow
from spotipy import SpotifyClientCredentials
from youtube_dl import YoutubeDL
from requests import get
from music_bot import MusicBot
from package.button_components import Button, ButtonRow

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                  'options': '-vn'}

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': False,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}


def config():
    with open("config.json") as json_file:
        return json.load(json_file)


def process_spotify_link(url):
    api_config = config()
    client_credentials_manager = SpotifyClientCredentials(client_id=api_config["spotify"]["client_id"],
                                                          client_secret=api_config["spotify"]["client_secret"])
    spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

    results = spotify.playlist_items(url)
    tracks = []
    count = 0
    do_break = False
    while True:
        results = results["items"]
        for result in results:
            track = result["track"]["name"] + " by"
            for artist in result["track"]["artists"]:
                track = track + " " + artist["name"]
            tracks.append(track)
            count += 1
        if do_break:
            break
        if count % 100 != 0:
            do_break = True
        results = spotify.playlist_items(url, offset=count)
    return tracks


def search(term):
    if "spotify.com" in term:
        return process_spotify_link(term)

    with YoutubeDL(YTDL_OPTIONS) as ydl:
        try:
            get(term)
        except:
            song = [ydl.extract_info(f"ytsearch:{term}", download=False)['entries'][0]]
        else:
            try:
                songs_data = ydl.extract_info(term, download=False, process=False)["entries"]
                songs = []
                for song in songs_data:
                    songs.append(song)
                return songs
            except KeyError:
                return [ydl.extract_info(term, download=False)]
        return song


async def join(ctx):
    if ctx.voice_client is not None:
        await ctx.voice_client.move_to(ctx.author.voice.channel)
    else:
        await ctx.author.voice.channel.connect()
        if not await channel_empty(ctx):
            await clear_messages(ctx)


async def clear_messages(ctx):
    print("Deleting all in " + str(ctx.channel))
    messages = await ctx.channel.history(limit=200).flatten()
    for message in messages:
        if str(message.author).strip() == "Sine Tunes#7449":
            await message.delete()


async def channel_empty(ctx):
    messages = await ctx.channel.history(limit=200).flatten()
    i = 0
    for message in messages:
        if str(message.author).strip() == "Sine Tunes#7449":
            i += 1
            if i > 1:
                return False
    return True


async def get_controls(ctx):
    messages = await ctx.channel.history(limit=200).flatten()
    for message in messages:
        if str(message.author).strip() == "Sine Tunes#7449":
            return message


class Music(Cog):

    def __init__(self, bot: MusicBot):
        self.bot = bot
        self._players = {}

    @property
    def players(self):
        for guild in self.bot.guilds:
            if guild.id not in self._players:
                self._players[guild.id] = Player(guild)
        return self._players

    def get_guild_player(self, guild_id):
        return self.players[guild_id]

    @cog_ext.cog_slash(name="play", guild_ids=[112051926538993664, 888604924387160074, 884243166981677096])
    async def _play(self, ctx: SlashContext, term):
        await join(ctx)
        await ctx.send(content="Searching " + term, delete_after=0.0001)
        voice: VoiceClient = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        player: Player = self.get_guild_player(ctx.guild_id)
        messages = await ctx.channel.history(limit=200).flatten()
        if len(messages) < 1:
            embed = Embed(title="Loading...")
            await ctx.send(embed=embed)
        player.queue.was_skipped = False
        previous_queue_length = player.queue.queue_size
        player.process_search(term)

        if voice.is_playing():
            await player.controls.update(ctx)
        else:
            if player.queue.has_next_song():
                player.queue.was_skipped = True
                player.queue.move_to(previous_queue_length)
                await player.play(ctx, player.queue.current_song())

            else:
                await player.play(ctx, player.queue.current_song())

    @cog_ext.cog_slash(name="clear", guild_ids=[112051926538993664, 888604924387160074, 884243166981677096])
    async def _clear(self, ctx: SlashContext):
        player: Player = self.get_guild_player(ctx.guild_id)
        player.queue.clear()
        await ctx.send(content="Clearing queue...", delete_after=2)

    @cog_ext.cog_slash(name="player", guild_ids=[112051926538993664, 888604924387160074, 884243166981677096])
    async def _player(self, ctx: SlashContext):
        await clear_messages(ctx)
        player: Player = self.get_guild_player(ctx.guild_id)
        player.queue.clear()
        embed = player.controls.update_embed()
        await ctx.send(embed=embed)

    @cog_ext.cog_component(components=["shuffle", "back", "play_pause", "forward", "repeat", "queue"])
    async def play(self, ctx: ComponentContext):
        button_pressed = ctx.component_id
        option_selected = ctx.selected_options
        player: Player = self.get_guild_player(ctx.guild_id)

        if button_pressed == "shuffle":
            player.controls.shuffle()
        if button_pressed == "back":
            await player.controls.back(ctx)
        if button_pressed == "play_pause":
            player.controls.play_pause(ctx)
        if button_pressed == "forward":
            await player.controls.forward(ctx)
        if button_pressed == "repeat":
            player.controls.repeat()

        try:
            if player.controls.buttons.get(custom_id=ctx.component_id).style == ButtonStyle.red:
                player.controls.buttons.get(custom_id=ctx.component_id).style = ButtonStyle.green
        except AttributeError:
            pass

        if option_selected is not None:
            position = int(option_selected[0])
            player.queue.was_skipped = True
            player.queue.move_to(player.queue.position + position)
            await player.play(ctx, player.queue.current_song())

        embed = player.controls.update_embed()
        await ctx.edit_origin(embed=embed, components=[player.controls.buttons.action_row, player.controls.select_menu])


class Player:

    def __init__(self, guild_id):
        self.guild_id = guild_id
        self.controls = Controls(self)
        self.queue = Queue(self)
        self.playing = False
        self.repeat = False

    def process_search(self, term):
        songs = search(term)
        if len(songs) == 1:
            try:
                song_object = Song(songs["title"])
            except TypeError:
                song_object = Song(songs)
            song_object.update(songs)
            self.queue.add_song(song_object)
        else:
            for song in songs:
                try:
                    song_object = Song(song["title"])
                except TypeError:
                    song_object = Song(song)
                self.queue.add_song(song_object)

    async def play(self, ctx, song):
        self.playing = True
        await join(ctx)
        voice: VoiceClient = ctx.voice_client
        voice.stop()
        song.download_song()

        voice.play(await FFmpegOpusAudio.from_probe(song.url, **FFMPEG_OPTIONS),
                   after=lambda e: self.queue.on_song_end(ctx))
        self.queue.was_skipped = False
        await self.controls.update(ctx)


class Controls:

    def __init__(self, player: Player):

        self.player = player
        self._button_array = [
            Button(create_button(style=ButtonStyle.grey, emoji="🔀", custom_id="shuffle")),
            Button(create_button(style=ButtonStyle.grey, emoji="⏮", custom_id="back")),
            Button(create_button(style=ButtonStyle.grey, emoji="⏸", custom_id="play_pause")),
            Button(create_button(style=ButtonStyle.grey, emoji="⏭", custom_id="forward")),
            Button(create_button(style=ButtonStyle.grey, emoji="🔁", custom_id="repeat")),
        ]
        self.buttons = ButtonRow(self._button_array)

    @property
    def select_menu(self):
        options = []
        for song in self.player.queue.songs[self.player.queue.position:]:
            if len(options) + 1 == 25:
                break
            if song.title is None:
                if len(song.term) > 99:
                    song.term = song.term.split("by")[0]
                options.append(create_select_option(label=song.term, value=str(len(options))))
            else:
                if len(song.title) > 99:
                    song.title = song.title.split("by")[0]
                options.append(create_select_option(label=song.title, value=str(len(options))))
        return create_actionrow(create_select(options, min_values=1, max_values=1, placeholder="Select from queue",
                                              custom_id="queue"))

    def resume(self, ctx):
        self.player.playing = True
        ctx.voice_client.resume()

    def pause(self, ctx):
        self.player.playing = False
        ctx.voice_client.pause()

    def shuffle(self):
        self.player.queue.shuffle()

    async def back(self, ctx):
        await self.player.queue.previous_song(ctx)

    def play_pause(self, ctx):

        button = self.buttons.get("play_pause")
        button_emoji = button.emoji["name"]

        if button_emoji == "▶":
            button.emoji["name"] = "⏸"
            self.resume(ctx)
        else:
            button.emoji["name"] = "▶"
            self.pause(ctx)

    async def forward(self, ctx):
        await self.player.queue.next_song(ctx)

    def repeat(self):
        button = self.buttons.get("repeat")
        if button.style == ButtonStyle.grey:
            button.style = ButtonStyle.green
            self.player.repeat = True
        else:
            button.style = ButtonStyle.grey
            self.player.repeat = False

    def update_embed(self):
        player = self.player
        current_song: Song = player.queue.current_song()
        next_song = player.queue.get_next_song()
        if next_song is not None:
            next_song.download_song()
            next_song = next_song.title
        embed = Embed(title=current_song.title, url=current_song.youtube_url)
        embed.set_thumbnail(url="https://i.gyazo.com/7df836dbb8b7e0570a384a835d82dcfc.png")
        embed.set_image(url=current_song.thumbnail)
        embed.add_field(name="Duration", value=current_song.duration)
        embed.add_field(name="Queue Length", value=str(len(player.queue.songs[player.queue.position:])))
        embed.add_field(name="Next Song", value=next_song)
        return embed

    async def update(self, ctx):

        player: Message = await get_controls(ctx)
        embed = self.update_embed()
        if self.player.playing:
            self.player.controls.buttons.get("play_pause").emoji = "⏸"
        else:
            self.player.controls.buttons.get("play_pause").emoji = "▶"
        if self.player.repeat:
            self.player.controls.buttons.get("repeat").style = ButtonStyle.green
        else:
            self.player.controls.buttons.get("repeat").style = ButtonStyle.grey
        try:
            await player.edit(embed=embed, components=[self.player.controls.buttons.action_row, self.select_menu])
        except AttributeError:
            await ctx.channel.send(embed=embed, components=[self.player.controls.buttons.action_row, self.select_menu])


class Queue:

    def __init__(self, player: Player):
        self.player = player
        self.songs = []
        self.position = 0
        self._queue_size = None
        self.was_skipped = False

    @property
    def queue_size(self):
        self._queue_size = len(self.songs)
        return self._queue_size

    def current_song(self):
        return self.songs[self.position]

    def has_next_song(self):
        return self.position != self.queue_size - 1

    def has_previous_song(self):
        return self.position != 0

    def add_song(self, song):
        self.songs.append(song)

    async def next_song(self, ctx):
        if self.has_next_song():
            self.position += 1
            song: Song = self.current_song()
            song.download_song()
            self.was_skipped = True
            await self.player.play(ctx, song)
        elif self.player.repeat:
            self.position = 0
            self.shuffle()
            song: Song = self.current_song()
            song.download_song()
            self.was_skipped = True
            await self.player.play(ctx, song)

    async def previous_song(self, ctx):
        if self.has_previous_song():
            self.position -= 1
            song: Song = self.current_song()
            song.download_song()
            self.was_skipped = True
            await self.player.play(ctx, song)

    def get_next_song(self):
        if self.has_next_song():
            return self.songs[self.position + 1]

    def get_previous_song(self):
        if self.has_previous_song():
            return self.songs[self.position - 1]

    def move_to(self, position):
        self.position = position

    def clear(self):
        self.songs = []
        self.position = 0

    def on_song_end(self, ctx):
        if self.was_skipped is False:
            voice: VoiceClient = ctx.voice_client
            future = asyncio.run_coroutine_threadsafe(self.next_song(ctx), voice.loop)
            try:
                future.result()
            except:
                print("We failed to play the next song")
                self.next_song(ctx)

    def shuffle(self):
        left_array = self.songs[:self.position]
        middle_array = [self.current_song()]
        right_array = self.songs[self.position + 1:]
        shuffle(right_array)
        self.songs = left_array + middle_array + right_array


class Song:

    def __init__(self, term):
        self.term = term
        self.title = None
        self.data = None
        self.url = None
        self.youtube_url = None
        self.thumbnail = None
        self.duration = None

    def update(self, data):
        self.data = data[0]
        self.title = self.data["title"]
        self.url = self.data['formats'][0]['url']
        self.youtube_url = self.data["webpage_url"]
        self.thumbnail = self.data["thumbnail"]
        seconds = int(self.data["duration"])
        self.duration = str(datetime.timedelta(seconds=seconds))

    def download_song(self):
        if not self.is_downloaded():
            self.update(search(self.term))

    def is_downloaded(self):
        return self.data is not None


def setup(bot: MusicBot):
    bot.add_cog(Music(bot))
