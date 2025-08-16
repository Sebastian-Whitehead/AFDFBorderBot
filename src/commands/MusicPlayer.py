"""
Music Player Commands for AFDFBorderBot
Handles music playback using Lavalink
"""

import asyncio
import os
import nextcord
from nextcord.ext import commands
import wavelink
from typing import cast
from src.config import IDS


class MusicPlayer(commands.Cog):
    """Music player functionality using Lavalink"""

    def __init__(self, bot):
        self.bot = bot
        bot.loop.create_task(self.connect_nodes())

    async def connect_nodes(self):
        """Connect to Lavalink nodes"""
        await self.bot.wait_until_ready()
        
        try:
            node = wavelink.Node(
                uri=f"http://{os.getenv('LAVALINK_HOST', 'localhost')}:{os.getenv('LAVALINK_PORT', '2333')}",
                password=os.getenv('LAVALINK_PASSWORD', 'youshallnotpass')
            )
            await wavelink.Pool.connect(client=self.bot, nodes=[node])
            print("✅ Connected to Lavalink")
        except Exception as e:
            print(f"❌ Failed to connect to Lavalink: {e}")

    @nextcord.slash_command(name="play", description="Play a song from YouTube, Spotify, SoundCloud, or other sources", guild_ids=[IDS['testing_guild']])
    async def play(
        self, 
        interaction: nextcord.Interaction,
        query: str = nextcord.SlashOption(description="Song name, YouTube URL, Spotify URL, or search query")
    ):
        """Play a song in voice channel"""
        
        if not interaction.user.voice:
            return await interaction.response.send_message(
                "❌ You need to be in a voice channel!", ephemeral=True
            )

        if not interaction.guild.voice_client:
            vc = await interaction.user.voice.channel.connect(cls=wavelink.Player)
        else:
            vc = cast(wavelink.Player, interaction.guild.voice_client)

        await interaction.response.defer()

        # Determine the source and search for tracks
        search_type = self.determine_search_type(query)
        tracks = await wavelink.Playable.search(query)
        
        if not tracks:
            embed = nextcord.Embed(
                title="❌ No tracks found!",
                description=f"Could not find any tracks for: `{query}`",
                color=0xff0000
            )
            embed.add_field(
                name="Supported Sources",
                value="• YouTube URLs and searches\n• Spotify URLs (tracks, albums, playlists)\n• SoundCloud URLs\n• Direct song searches",
                inline=False
            )
            return await interaction.followup.send(embed=embed)

        # Handle different track types (single track vs playlist)
        if hasattr(tracks, 'tracks') and tracks.tracks:  # It's a playlist
            track_list = tracks.tracks
            embed = nextcord.Embed(
                title="🎵 Playlist Added to Queue",
                description=f"**{tracks.name}** - {len(track_list)} tracks",
                color=0x00ff00
            )
            embed.add_field(name="Source", value=search_type, inline=True)
            embed.add_field(name="Requested by", value=interaction.user.mention, inline=True)
            
            for track in track_list:
                if vc.playing:
                    await vc.queue.put_wait(track)
                else:
                    await vc.play(track)
                    vc.playing = True  # Set to true after first track
                    
        else:  # Single track
            track = tracks[0] if isinstance(tracks, list) else tracks
            
            if vc.playing:
                await vc.queue.put_wait(track)
                embed = nextcord.Embed(
                    title="🎵 Added to Queue",
                    description=f"**{track.title}** by {track.author}",
                    color=0x00ff00
                )
                embed.add_field(name="Duration", value=self.format_time(track.length), inline=True)
                embed.add_field(name="Position in Queue", value=f"#{vc.queue.count}", inline=True)
                embed.add_field(name="Source", value=search_type, inline=True)
            else:
                await vc.play(track)
                embed = nextcord.Embed(
                    title="🎵 Now Playing",
                    description=f"**{track.title}** by {track.author}",
                    color=0x00ff00
                )
                embed.add_field(name="Duration", value=self.format_time(track.length), inline=True)
                embed.add_field(name="Requested by", value=interaction.user.mention, inline=True)
                embed.add_field(name="Source", value=search_type, inline=True)

            if hasattr(track, 'artwork') and track.artwork:
                embed.set_thumbnail(url=track.artwork)

        await interaction.followup.send(embed=embed)

    @nextcord.slash_command(name="pause", description="Pause the current song", guild_ids=[IDS['testing_guild']])
    async def pause(self, interaction: nextcord.Interaction):
        """Pause the current song"""
        vc = cast(wavelink.Player, interaction.guild.voice_client)
        
        if not vc or not vc.playing:
            return await interaction.response.send_message("❌ Nothing is playing!", ephemeral=True)

        await vc.pause(True)
        await interaction.response.send_message("⏸️ Paused the music!")

    @nextcord.slash_command(name="resume", description="Resume the current song", guild_ids=[IDS['testing_guild']])
    async def resume(self, interaction: nextcord.Interaction):
        """Resume the current song"""
        vc = cast(wavelink.Player, interaction.guild.voice_client)
        
        if not vc or not vc.paused:
            return await interaction.response.send_message("❌ Nothing is paused!", ephemeral=True)

        await vc.pause(False)
        await interaction.response.send_message("▶️ Resumed the music!")

    @nextcord.slash_command(name="skip", description="Skip the current song", guild_ids=[IDS['testing_guild']])
    async def skip(self, interaction: nextcord.Interaction):
        """Skip the current song"""
        vc = cast(wavelink.Player, interaction.guild.voice_client)
        
        if not vc or not vc.playing:
            return await interaction.response.send_message("❌ Nothing is playing!", ephemeral=True)

        await vc.skip()
        await interaction.response.send_message("⏭️ Skipped the song!")

    @nextcord.slash_command(name="stop", description="Stop music and disconnect", guild_ids=[IDS['testing_guild']])
    async def stop(self, interaction: nextcord.Interaction):
        """Stop music and disconnect from voice channel"""
        vc = cast(wavelink.Player, interaction.guild.voice_client)
        
        if not vc:
            return await interaction.response.send_message("❌ Not connected to a voice channel!", ephemeral=True)

        await vc.disconnect()
        await interaction.response.send_message("🔇 Stopped music and disconnected!")

    @nextcord.slash_command(name="queue", description="Show the music queue", guild_ids=[IDS['testing_guild']])
    async def queue(self, interaction: nextcord.Interaction):
        """Display the current music queue"""
        vc = cast(wavelink.Player, interaction.guild.voice_client)
        
        if not vc:
            return await interaction.response.send_message("❌ Not connected to a voice channel!", ephemeral=True)

        embed = nextcord.Embed(title="🎵 Music Queue", color=0x00ff00)
        
        if vc.current:
            current_info = f"**{vc.current.title}** by {vc.current.author}"
            if hasattr(vc.current, 'length') and vc.current.length:
                current_info += f" `({self.format_time(vc.current.length)})`"
            embed.add_field(
                name="🎵 Now Playing",
                value=current_info,
                inline=False
            )
            
            # Add progress bar if possible
            if hasattr(vc, 'position') and vc.current.length:
                progress = int((vc.position / vc.current.length) * 20)
                progress_bar = "█" * progress + "░" * (20 - progress)
                embed.add_field(
                    name="⏱️ Progress",
                    value=f"`{self.format_time(vc.position)} {progress_bar} {self.format_time(vc.current.length)}`",
                    inline=False
                )
        
        if vc.queue.is_empty:
            if not vc.current:
                embed.description = "The queue is empty! Use `/play` to add some music."
            else:
                embed.add_field(name="⏭️ Up Next", value="No songs in queue", inline=False)
        else:
            queue_list = []
            total_duration = 0
            
            for i, track in enumerate(vc.queue[:10], 1):  # Show first 10 songs
                duration_str = self.format_time(track.length) if track.length else "Unknown"
                if track.length:
                    total_duration += track.length
                queue_list.append(f"`{i}.` **{track.title}** by {track.author} `({duration_str})`")

            embed.add_field(
                name="⏭️ Up Next",
                value="\n".join(queue_list),
                inline=False
            )

            # Queue statistics
            queue_info = []
            if len(vc.queue) > 10:
                queue_info.append(f"And {len(vc.queue) - 10} more songs...")
            if total_duration > 0:
                queue_info.append(f"Total duration: {self.format_time(total_duration)}")
            
            if queue_info:
                embed.add_field(
                    name="📊 Queue Info", 
                    value="\n".join(queue_info),
                    inline=False
                )

        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="volume", description="Set the music volume", guild_ids=[IDS['testing_guild']])
    async def volume(
        self, 
        interaction: nextcord.Interaction,
        volume: int = nextcord.SlashOption(description="Volume (0-100)", min_value=0, max_value=100)
    ):
        """Set the music volume"""
        vc = cast(wavelink.Player, interaction.guild.voice_client)
        
        if not vc:
            return await interaction.response.send_message("❌ Not connected to a voice channel!", ephemeral=True)

        await vc.set_volume(volume)
        await interaction.response.send_message(f"🔊 Volume set to {volume}%!")

    @nextcord.slash_command(name="nowplaying", description="Show detailed information about the current song", guild_ids=[IDS['testing_guild']])
    async def nowplaying(self, interaction: nextcord.Interaction):
        """Show detailed information about the currently playing song"""
        vc = cast(wavelink.Player, interaction.guild.voice_client)
        
        if not vc or not vc.current:
            return await interaction.response.send_message("❌ Nothing is currently playing!", ephemeral=True)

        track = vc.current
        embed = nextcord.Embed(
            title="🎵 Now Playing",
            description=f"**{track.title}**",
            color=0x00ff00
        )
        
        # Basic track info
        if track.author:
            embed.add_field(name="👤 Artist", value=track.author, inline=True)
        if track.length:
            embed.add_field(name="⏱️ Duration", value=self.format_time(track.length), inline=True)
        
        # Playback status
        status = "⏸️ Paused" if vc.paused else "▶️ Playing"
        embed.add_field(name="📊 Status", value=status, inline=True)
        
        # Volume and position
        embed.add_field(name="🔊 Volume", value=f"{vc.volume}%", inline=True)
        
        if hasattr(vc, 'position') and track.length:
            position_str = f"{self.format_time(vc.position)} / {self.format_time(track.length)}"
            embed.add_field(name="📍 Position", value=position_str, inline=True)
            
            # Progress bar
            progress = min(int((vc.position / track.length) * 20), 20)
            progress_bar = "█" * progress + "░" * (20 - progress)
            embed.add_field(
                name="⏯️ Progress",
                value=f"`{progress_bar}`",
                inline=False
            )
        
        # Track source info
        source_info = self.determine_search_type(track.uri if hasattr(track, 'uri') else "")
        embed.add_field(name="🌐 Source", value=source_info, inline=True)
        
        # Queue info
        if not vc.queue.is_empty:
            embed.add_field(name="⏭️ Queue", value=f"{len(vc.queue)} songs waiting", inline=True)
        else:
            embed.add_field(name="⏭️ Queue", value="Empty", inline=True)

        # Thumbnail
        if hasattr(track, 'artwork') and track.artwork:
            embed.set_thumbnail(url=track.artwork)

        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="clear", description="Clear the music queue", guild_ids=[IDS['testing_guild']])
    async def clear(self, interaction: nextcord.Interaction):
        """Clear the music queue"""
        vc = cast(wavelink.Player, interaction.guild.voice_client)
        
        if not vc:
            return await interaction.response.send_message("❌ Not connected to a voice channel!", ephemeral=True)
            
        if vc.queue.is_empty:
            return await interaction.response.send_message("❌ The queue is already empty!", ephemeral=True)

        cleared_count = len(vc.queue)
        vc.queue.clear()
        
        embed = nextcord.Embed(
            title="🗑️ Queue Cleared",
            description=f"Removed {cleared_count} songs from the queue",
            color=0xff9900
        )
        
        await interaction.response.send_message(embed=embed)

    @staticmethod
    def format_time(milliseconds: int) -> str:
        """Format time from milliseconds to MM:SS"""
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    @staticmethod
    def determine_search_type(query: str) -> str:
        """Determine the source type based on the query"""
        if "spotify.com" in query:
            if "/track/" in query:
                return "🎵 Spotify Track"
            elif "/album/" in query:
                return "💿 Spotify Album"
            elif "/playlist/" in query:
                return "📋 Spotify Playlist"
            else:
                return "🎵 Spotify"
        elif "youtube.com" in query or "youtu.be" in query:
            if "playlist" in query:
                return "📋 YouTube Playlist"
            else:
                return "📺 YouTube"
        elif "soundcloud.com" in query:
            return "🔊 SoundCloud"
        elif query.startswith("http"):
            return "🌐 Direct URL"
        else:
            return "🔍 Search"

    @nextcord.slash_command(name="sources", description="Show supported music sources and how to use them", guild_ids=[IDS['testing_guild']])
    async def sources(self, interaction: nextcord.Interaction):
        """Display information about supported music sources"""
        embed = nextcord.Embed(
            title="🎵 Supported Music Sources",
            description="Here are all the ways you can play music:",
            color=0x00ff00
        )
        
        embed.add_field(
            name="🔍 Search by Name",
            value="Just type the song name: `/play Never Gonna Give You Up`",
            inline=False
        )
        
        embed.add_field(
            name="📺 YouTube",
            value="• Video URLs: `https://youtube.com/watch?v=...`\n• Playlist URLs: `https://youtube.com/playlist?list=...`\n• Search: `/play ytsearch:song name`",
            inline=False
        )
        
        embed.add_field(
            name="🎵 Spotify",
            value="• Track URLs: `https://open.spotify.com/track/...`\n• Album URLs: `https://open.spotify.com/album/...`\n• Playlist URLs: `https://open.spotify.com/playlist/...`",
            inline=False
        )
        
        embed.add_field(
            name="🔊 SoundCloud",
            value="• Track URLs: `https://soundcloud.com/...`\n• Search: `/play scsearch:song name`",
            inline=False
        )
        
        embed.add_field(
            name="📝 Tips",
            value="• For best results with Spotify, make sure your .env file has valid `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`\n• YouTube fallback is automatic for Spotify tracks\n• You can queue multiple songs by using playlists",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="search", description="Search for music on specific platforms", guild_ids=[IDS['testing_guild']])
    async def search(
        self,
        interaction: nextcord.Interaction,
        query: str = nextcord.SlashOption(description="Search query"),
        platform: str = nextcord.SlashOption(
            description="Platform to search on",
            choices=["YouTube", "SoundCloud", "Auto"]
        )
    ):
        """Search for music on specific platforms"""
        await interaction.response.defer()
        
        # Format query based on platform
        if platform == "YouTube":
            search_query = f"ytsearch:{query}"
        elif platform == "SoundCloud":
            search_query = f"scsearch:{query}"
        else:
            search_query = query
            
        tracks = await wavelink.Playable.search(search_query)
        
        if not tracks:
            return await interaction.followup.send(f"❌ No tracks found on {platform}!")
        
        # Show search results (first 10)
        embed = nextcord.Embed(
            title=f"🔍 Search Results - {platform}",
            description=f"Found {len(tracks)} results for: `{query}`",
            color=0x00ff00
        )
        
        results = []
        for i, track in enumerate(tracks[:10], 1):
            duration = self.format_time(track.length) if track.length else "Unknown"
            results.append(f"`{i}.` **{track.title}** by {track.author} `({duration})`")
            
        embed.add_field(
            name="📋 Results",
            value="\n".join(results),
            inline=False
        )
        
        embed.add_field(
            name="💡 How to Play",
            value=f"Use `/play {tracks[0].title}` to play the first result, or copy a specific title.",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        """Event fired when a Lavalink node is ready"""
        print(f"🎵 Lavalink node {payload.node.uri} is ready!")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        """Event fired when a track ends"""
        player = payload.player
        if not player.queue.is_empty:
            next_track = await player.queue.get_wait()
            await player.play(next_track)


def setup(bot):
    bot.add_cog(MusicPlayer(bot))
