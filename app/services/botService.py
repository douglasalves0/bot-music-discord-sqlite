import discord
from discord.ext import commands
from youtube_dl import YoutubeDL
from database.repositories.PlaylistRepo import PlaylistRepo
from database.repositories.SongRepo import SongRepo

class BotMusic(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.is_playing = False
        self.music_queue = []
        self.YDL_OPTIONS = {"format": "bestaudio", "noplaylist": "True"}
        self.FFMPEG_OPTIONS = {"before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", "options": "-vn"}
        self.voice = ""



    def searchYoutube(self, music):
        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info("ytsearch:%s" % music, download=False)["entries"][0]
            except Exception:
                return False
        return {"source": info["formats"][0]["url"], "title": info["title"]}



    def play_next(self):
        if(len(self.music_queue) > 0):
            self.is_playing = True
            m_url = self.music_queue[0][0]["source"]
            self.music_queue.pop(0)
            self.voice.play(discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS), after=lambda e: self.play_next())
        else:
            self.is_playing = False
  


    async def play_music(self):
        if(len(self.music_queue) > 0):
            self.is_playing = True
            m_url = self.music_queue[0][0]["source"]
            if(self.voice == "" or not self.voice.is_connected() or self.voice == None):
                self.voice = await self.music_queue[0][1].connect()
            else:
                await self.voice.move_to(self.music_queue[0][1])
            self.music_queue.pop(0)
            self.voice.stop()
            self.voice.play(discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS), after=lambda e: self.play_next())
        else:
            self.is_playing = False
            


    @commands.command(name="play", help="Toca o som dj")
    async def play(self, ctx, *args):
        query = " ".join(args)
        voice_channel = ctx.author.voice.channel
        if voice_channel == None:
            await ctx.send("Conecte-se a um canal de voz!")
        else:
            song = self.searchYoutube(query)
            if type(song) == type(True):
                await ctx.send("N??o foi poss??vel baixar a m??sica")
            else:
                await ctx.send("M??sica adicionada ?? fila")
                self.music_queue.append([song, voice_channel, query])
                if self.is_playing == False:
                    await self.play_music()



    @commands.command(name="skip", help="Pra pular aquela m??sica que o caba t?? abusado")
    async def skip(self, ctx):
        if not (self.voice == "" or not self.voice.is_connected() or self.voice == None):
            self.voice.stop()
            await self.play_music()
        else:
            await ctx.send("Se conecte ao canal de voz primeiro!")
            return


  
    @commands.command(name="leave", help="Disconnecting bot from VC")
    async def leave(self, ctx):
        if(self.voice == "" or not self.voice.is_connected() or self.voice == None):
            await ctx.send("Eu n??o estou em nenhum canal de voz :cry:")
        else:
            await self.voice.disconnect()



    @commands.command(name="queue", help="Lista todas as m??sicas da fila")
    async def queue(self, ctx):
        saida = "```python\nLISTA DE M??SICAS\n"
        for i in range(len(self.music_queue)):
            saida += f"[{i}] {self.music_queue[i][2]}.\n" 
        saida += "```"
        await ctx.send(saida)



    @commands.command(name="addplaylist", help="Cria uma playlist de m??sicas")
    async def addplaylist(self, ctx, *name):
        try:
            if(len(name) > 1):
                await ctx.send("O nome da playlist n??o pode conter espa??os")
                return
            name = name[0]
            playlist = PlaylistRepo.findPlaylistByName(name)
            if(len(playlist) > 0):
                await ctx.send("Playlist j?? existe, por favor crie uma nova")
            else:
                PlaylistRepo.save(name)
                await ctx.send("Playlist criada com sucesso!")
        except Exception:
            return False


  
    @commands.command(name="addto", help="Adiciona a m??sica na playlist, ex: !add playlist m??sica")
    async def add(self, ctx, *content):
        try: 
            playlistName = content[0]
            list = []
            for i in range(1,len(content)):
                list.append(content[i])
            musicName = " ".join(list)
            foundPlaylists = PlaylistRepo.findPlaylistByName(playlistName)
            if(len(foundPlaylists) > 0):
                SongRepo.save(musicName, playlistName)
                await ctx.send("M??sica adicionada ?? playlist %s"%(playlistName))
            else:
                await ctx.send("Playlist inexistente")
        except:
            return False



    @commands.command(name="playlists", help="Retorna todas as playlists")
    async def playlists(self, ctx):
        playlists = PlaylistRepo.findAll()
        saida = "```python\nLISTA DE PLAYLISTS\n"
        for json in playlists:
            saida += (json["name"]) + "\n"
        saida += "```"
        await ctx.send(saida)



    @commands.command(name="listplaylist", help="Lista as m??sicas da playlist")
    async def listPlaylist(self, ctx, *name):
        try:
            playlistName = name[0]
            foundPlaylists = PlaylistRepo.findPlaylistByName(playlistName)
            if(len(foundPlaylists) == 0):
                await ctx.send("Playlist inexistente")
                return
            foundSongs = SongRepo.findByPlaylist(playlistName)
            if(len(foundSongs) == 0):
                await ctx.send("Voc?? ainda n??o adicionou nenhuma m??sica a essa playlist")
                return
            saida = f"```python\nM??sicas da playlist **{playlistName}**\n"
            for i in range(len(foundSongs)):
                name = foundSongs[i]["name"]
                saida += f"[{i}] {name}.\n"
            saida += "```"
            await ctx.send(saida)
        except:
            await ctx.send("Um erro ocorreu")



    @commands.command(name="playplaylist", help="Toca as m??sicas da playlist")
    async def playPlaylist(self, ctx, *name):
        try:
            voice_channel = ctx.author.voice.channel
            if voice_channel==None or voice_channel=="":
                await ctx.send("Conecte a um canal de voz!")
            playlistName = name[0]
            foundSongs = SongRepo.findByPlaylist(playlistName)
            if(len(foundSongs) == 0):
                await ctx.send("Voc?? ainda n??o adicionou nenhuma m??sica a essa playlist ou ela n??o existe")
                return
            songsNames = []
            for music in foundSongs:
                songsNames.append(music['name'])
            await ctx.send("Baixando m??sicas da playlist...")
            if self.voice != "" and self.voice.is_connected():
                self.voice.stop()
            self.music_queue.clear()
            for i in range(len(songsNames)):
                song = self.searchYoutube(songsNames[i])
                self.music_queue.append([song, voice_channel, songsNames[i]])
            await self.play_music()
            await ctx.send("Tocando playlist")
        except:
            return