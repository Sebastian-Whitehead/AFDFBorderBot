# AFDF Border Bot

A Discord bot designed for the Aegean Federation Defense Forces (AFDF) server to manage border control, member enlistment, event scheduling, and automated monitoring of border officers.

## 🎯 Features

### Border Control Management

- **Member Approval**: Border officers can approve new members entering the server
- **Automatic Role Assignment**: Assigns appropriate roles to approved members
- **Welcome System**: Sends customized welcome messages with embeds when new citizens are approved

### Military Enlistment

- **Army Enrollment**: Leadership can enlist members into military roles
- **Role Management**: Automatically assigns military department and enlisted roles

### Event Management

- **Weekend Events**: Create standard weekend event series (Friday, Saturday, Sunday)
- **Attendance Tracking**: Log attendance for events in voice channels
- **Event Notifications**: Automatically notify subscribed members when events start

### Border Officer Monitoring

- **24/7 Monitoring**: Continuously monitors if border officers are online
- **Automatic Notifications**: Posts closure messages when no border officers are available
- **Status Updates**: Updates channel messages based on officer availability

### Additional Features

- **Ping Command**: Interactive ping command with random easter egg
- **Error Handling**: Comprehensive error handling for role/permission issues
- **Configuration-Based**: All settings managed through `config.json`

### Music Player 🎵

- **Multi-Platform Support**: Play music from YouTube, Spotify, SoundCloud, and more
- **Queue Management**: Advanced queue system with playlist support
- **Volume Control**: Adjustable volume with real-time controls
- **Now Playing Info**: Detailed track information with progress bars
- **Search Features**: Platform-specific search and auto-detection

## 🚀 Installation

### Quick Start with Docker (Recommended)

The easiest way to run the bot is using Docker. See **[DOCKER.md](DOCKER.md)** for detailed Docker setup and usage instructions.

### Manual Installation

### Prerequisites

- Python 3.10 or higher
- Discord Bot Token
- PostgreSQL database (optional, for advanced features)

### Setup

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd AFDFBorderBot
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration**

   Create a `.env` file in the root directory:

   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   
   # Optional: For music player Spotify support
   SPOTIFY_CLIENT_ID=your_spotify_client_id_here
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here
   ```

4. **Configure the bot**

   Edit `config.json` with your server-specific IDs:

   ```json
   {
     "testing_guild": YOUR_GUILD_ID,
     "channels": {
       "log_txt": YOUR_LOG_CHANNEL_ID,
       "main_txt": YOUR_MAIN_CHANNEL_ID,
       "checkpoint_txt": YOUR_CHECKPOINT_CHANNEL_ID,
       "events_vc": YOUR_EVENTS_VOICE_CHANNEL_ID,
       "welcome_txt": YOUR_WELCOME_CHANNEL_ID
     },
     "roles": {
       "leadership": YOUR_LEADERSHIP_ROLE_ID,
       "border_officer": YOUR_BORDER_OFFICER_ROLE_ID,
       "civil_servant": YOUR_CIVIL_SERVANT_ROLE_ID
     }
   }
   ```

5. **Run the bot**

   ```bash
   python main.py
   ```

## 📁 Project Structure

```text
AFDFBorderBot/
├── main.py                    # Main bot file and entry point
├── config.json               # Configuration file with IDs (legacy)
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (create this)
├── .env.example              # Environment template
├── docker-compose.yml        # Docker services configuration
├── Dockerfile               # Bot container definition
├── app.bat                  # Control script for Docker services
├── MUSIC_SETUP.md          # Music player setup guide
├── MUSIC_COMMANDS.md       # Quick music commands reference
├── src/
│   ├── config.py            # Centralized configuration management
│   ├── commands/           # Bot commands (cogs)
│   │   ├── Checkpoint.py   # Border control commands
│   │   ├── Enlistment.py   # Military enlistment system
│   │   ├── GuildEvent.py   # Event management commands
│   │   └── MusicPlayer.py  # Music player commands
│   └── listeners/          # Event listeners (cogs)
│       ├── BorderOfficerMonitor.py   # Background monitoring
│       └── JoinLeaveHandler.py       # Join/leave events
├── embeds/
│   ├── newcitizen-main.json     # Welcome message embed
│   ├── member_join-welcome.json  # Join message template
│   └── member_leave-welcome.json # Leave message template
├── lavalink/
│   └── application.yml      # Lavalink music server configuration
├── pgadmin-data/           # pgAdmin data volume
└── __pycache__/            # Python cache files
```

## 🤖 Commands

### Border Control

- `/approve <user>` - Approve a member's border crossing request
  - **Required Role**: Border Officer
  - **Description**: Removes joining role, adds citizen roles, sends welcome message

### Military Operations

- `/enlist <user>` - Enlist a member in the military
  - **Required Role**: Leadership
  - **Description**: Assigns enlisted and military department roles

### Event Commands

- `/create_weekend_events <friday_hour> <saturday_hour> <sunday_hour>` - Create weekend event series
  - **Required Role**: Leadership
  - **Description**: Creates scheduled events for the next weekend

- `/attendance` - Take attendance for current voice channel
  - **Required Role**: Civil Servant
  - **Description**: Logs who is present in the events voice channel

### General

- `/ping` - Test bot responsiveness
  - **Available to**: Everyone
  - **Description**: Responds with "Pong!" (with rare easter egg)

### Music Player Commands 🎵

- `/play <query>` - Play music from any supported source
  - **Available to**: Everyone
  - **Description**: Play songs from YouTube, Spotify, SoundCloud, or search by name

- `/pause` / `/resume` - Control playback
  - **Available to**: Everyone
  - **Description**: Pause or resume the current song

- `/skip` / `/stop` - Playback control
  - **Available to**: Everyone
  - **Description**: Skip current song or stop and disconnect

- `/queue` - Show music queue
  - **Available to**: Everyone
  - **Description**: Display current queue with detailed information

- `/volume <0-100>` - Set volume
  - **Available to**: Everyone
  - **Description**: Adjust playback volume

- `/nowplaying` - Current song info
  - **Available to**: Everyone
  - **Description**: Show detailed information about the current song

- `/search <query> <platform>` - Search specific platforms
  - **Available to**: Everyone
  - **Description**: Search for music on YouTube, SoundCloud, or auto-detect

- `/sources` - Show supported sources
  - **Available to**: Everyone
  - **Description**: Display all supported music sources and usage instructions

For detailed music setup instructions, see **[MUSIC_SETUP.md](MUSIC_SETUP.md)**

## ⚙️ Configuration

### Required Discord Permissions

- Manage Roles
- Send Messages
- Manage Messages
- View Channels
- Connect to Voice Channels
- Speak in Voice Channels (for music playback)
- Manage Events
- Embed Links
- Use Slash Commands
- Use Voice Activity (for music bot functionality)

### Role Hierarchy

Ensure the bot's role is positioned above all roles it needs to manage in your Discord server's role hierarchy.

## 🔧 Customization

### Embed Messages

Customize welcome and notification messages by editing JSON files in the `embeds/` directory.

### Monitoring Intervals

Adjust the border officer monitoring frequency by modifying `CHECK_INTERVAL` in `BorderOfficerMonitor.py`.

### Role IDs

Update role and channel IDs in `config.json` to match your server setup.

## 🐛 Troubleshooting

### Common Issues

1. **Bot not responding to commands**
   - Check if the bot has proper permissions
   - Verify the guild ID in config.json matches your server

2. **Role assignment errors**
   - Ensure bot role is higher than roles it's trying to assign
   - Check if role IDs in config.json are correct

3. **Missing dependencies**
   - Run `pip install -r requirements.txt` to install all required packages

4. **Environment variables not loading**
   - Ensure `.env` file is in the root directory
   - Check that `DISCORD_TOKEN` is properly set

## 📝 Dependencies

- **nextcord**: Modern Discord API wrapper
- **python-dotenv**: Environment variable management
- **Pillow**: Image processing capabilities
- **psycopg**: PostgreSQL database adapter
- **SQLAlchemy**: Database ORM
- **wavelink**: Lavalink audio wrapper for music functionality
- **yt-dlp**: YouTube and media downloader

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support with this bot:

1. Check the troubleshooting section above
2. Review Discord bot permissions
3. Verify configuration settings
4. Open an issue on the repository

---

**Note**: This bot is specifically designed for the Aegean Federation Defense Forces Discord server. You may need to modify role IDs, channel IDs, and embed content to fit your specific server needs.
