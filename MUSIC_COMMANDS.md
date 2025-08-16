# 🎵 Quick Music Commands Reference

## Basic Commands
| Command | Description | Example |
|---------|-------------|---------|
| `/play <query>` | Play music from any source | `/play Never Gonna Give You Up` |
| `/pause` | Pause current song | `/pause` |
| `/resume` | Resume paused song | `/resume` |
| `/skip` | Skip current song | `/skip` |
| `/stop` | Stop and disconnect | `/stop` |
| `/volume <0-100>` | Set volume | `/volume 75` |

## Queue Management
| Command | Description | Example |
|---------|-------------|---------|
| `/queue` | Show music queue | `/queue` |
| `/clear` | Clear the queue | `/clear` |
| `/nowplaying` | Current song info | `/nowplaying` |

## Search & Sources
| Command | Description | Example |
|---------|-------------|---------|
| `/search <query> <platform>` | Search specific platform | `/search lofi YouTube` |
| `/sources` | Show supported sources | `/sources` |

## Supported URLs
- **Spotify**: `https://open.spotify.com/track/...` (tracks, albums, playlists)
- **YouTube**: `https://youtube.com/watch?v=...` (videos, playlists)
- **SoundCloud**: `https://soundcloud.com/...`

## Quick Examples
```
/play https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh
/play https://www.youtube.com/watch?v=dQw4w9WgXcQ
/play Never Gonna Give You Up
/search rick astley YouTube
/volume 50
/queue
```

## Setup Required
1. Set `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` in `.env`
2. Start bot with: `./app.bat start bot`
3. Join a voice channel before playing music

For detailed setup instructions, see `MUSIC_SETUP.md`.
