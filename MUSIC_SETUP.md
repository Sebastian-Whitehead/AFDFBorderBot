# 🎵 Music Player Setup Guide

This guide will help you set up the music player with Spotify and YouTube support for your AFDFBorderBot.

## 🚀 Quick Start

### 1. Environment Variables

Copy `.env.example` to `.env` and fill in the required values:

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` with your values:
```bash
DISCORD_TOKEN=your_discord_bot_token_here
SPOTIFY_CLIENT_ID=your_spotify_client_id_here
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here
```

### 2. Spotify API Setup (Required for Spotify support)

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Log in with your Spotify account
3. Click "Create App"
4. Fill in:
   - **App Name**: AFDFBorderBot Music Player
   - **App Description**: Discord bot music player
   - **Redirect URI**: `http://localhost` (can be anything for this use case)
5. Accept the terms and create the app
6. Copy the **Client ID** and **Client Secret** to your `.env` file

### 3. Start the Bot

Using Docker (Recommended):
```bash
# Start all services (bot + database + music)
./app.bat start full

# Or start just the bot and music services
./app.bat start bot
```

Manual start:
```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python main.py
```

## 🎵 Music Commands

### Basic Commands

- `/play <query>` - Play a song from YouTube, Spotify, or search
- `/pause` - Pause the current song
- `/resume` - Resume the current song
- `/skip` - Skip the current song
- `/stop` - Stop music and disconnect
- `/queue` - Show the music queue
- `/volume <0-100>` - Set the volume

### Advanced Commands

- `/nowplaying` - Show detailed information about the current song
- `/clear` - Clear the music queue
- `/search <query> <platform>` - Search for music on specific platforms
- `/sources` - Show all supported music sources

## 🌐 Supported Sources

### 🎵 Spotify
- **Track URLs**: `https://open.spotify.com/track/...`
- **Album URLs**: `https://open.spotify.com/album/...`
- **Playlist URLs**: `https://open.spotify.com/playlist/...`
- **Search**: Just type the song name, Spotify will be searched automatically

### 📺 YouTube
- **Video URLs**: `https://youtube.com/watch?v=...`
- **Playlist URLs**: `https://youtube.com/playlist?list=...`
- **Search**: `/search query YouTube` or `/play ytsearch:song name`

### 🔊 SoundCloud
- **Track URLs**: `https://soundcloud.com/...`
- **Search**: `/search query SoundCloud` or `/play scsearch:song name`

### 🌐 Other Sources
- **Direct URLs**: Any direct audio file URL
- **Bandcamp**: Bandcamp track URLs
- **Twitch**: Twitch stream URLs
- **Vimeo**: Vimeo video URLs

## 🔧 Advanced Configuration

### Lavalink Configuration

The music player uses Lavalink as the audio server. Configuration is in `lavalink/application.yml`.

Key settings:
- **Buffer settings**: Adjust for better audio quality vs. latency
- **Search limits**: Control how many results are loaded from playlists
- **Plugin configuration**: Spotify API settings

### Docker Configuration

Services in `docker-compose.yml`:
- **lavalink**: Audio server with plugin support
- **bot**: Discord bot
- **postgres**: Database for bot data
- **pgadmin**: Database management interface

## 📝 Usage Examples

### Playing Spotify Content
```
/play https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh
/play https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
/play Never Gonna Give You Up
```

### Playing YouTube Content
```
/play https://www.youtube.com/watch?v=dQw4w9WgXcQ
/play https://www.youtube.com/playlist?list=PLrAXtmRdnEQy6nuLMaafGeiDFOIqHhSP_
/search Rick Astley YouTube
```

### Advanced Usage
```
/volume 75
/search lofi hip hop YouTube
/queue
/nowplaying
/clear
```

## 🐛 Troubleshooting

### Common Issues

**"❌ No tracks found!"**
- Check your internet connection
- Verify Spotify credentials in `.env`
- Make sure Lavalink service is running
- Try a different search query

**"❌ Not connected to a voice channel!"**
- Join a voice channel before using music commands
- Make sure the bot has permissions to join voice channels

**"❌ Failed to connect to Lavalink"**
- Check that Lavalink container is running: `docker ps`
- Check Lavalink logs: `docker logs afdfborderbot-lavalink-1`
- Verify `LAVALINK_PASSWORD` matches in both `.env` and `docker-compose.yml`

**Spotify tracks not playing**
- Verify `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` in `.env`
- Restart the Lavalink service: `./app.bat restart`
- Check Lavalink logs for authentication errors

### Getting Help

1. Check the container logs:
   ```bash
   docker logs afdfborderbot-bot-1
   docker logs afdfborderbot-lavalink-1
   ```

2. Verify services are running:
   ```bash
   docker ps
   ```

3. Test Lavalink directly:
   ```bash
   curl http://localhost:2333/version
   ```

## 🔒 Security Notes

- Keep your Spotify API credentials secure
- Don't commit `.env` file to version control
- Use environment-specific credentials for production
- Monitor API usage in Spotify Developer Dashboard

## 🎯 Performance Tips

- Use Docker for consistent performance
- Monitor Lavalink memory usage (configured for 1GB max)
- Consider upgrading server resources for high-traffic bots
- Use playlists for batch operations instead of individual tracks

## 📚 Additional Resources

- [Wavelink Documentation](https://wavelink.dev/)
- [Lavalink Documentation](https://lavalink.dev/)
- [Spotify Web API Documentation](https://developer.spotify.com/documentation/web-api/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
