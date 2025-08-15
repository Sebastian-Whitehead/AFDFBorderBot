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

## 🚀 Installation

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
├── config.json               # Configuration file with IDs
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (create this)
├── src/
│   ├── checkpointManagement.py    # Border control commands
│   ├── enlistment.py             # Military enlistment system
│   ├── events.py                 # Event management commands
│   ├── passport_edit.py          # Image processing utilities
│   └── Routines/
│       └── BorderOfficerMonitor.py   # Background monitoring task
├── embeds/
│   ├── newcitizen-main.json     # Welcome message embed
│   ├── member_join-welcome.json  # Join message template
│   └── member_leave-welcome.json # Leave message template
└── __pycache__/              # Python cache files
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

## ⚙️ Configuration

### Required Discord Permissions

- Manage Roles
- Send Messages
- Manage Messages
- View Channels
- Connect to Voice Channels
- Manage Events
- Embed Links
- Use Slash Commands

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
