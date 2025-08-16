# AFDFBorderBot TODO

## 🎯 Priority Commands

### Member Management

- [ ] `/promote <user> <rank>` - Promote users and update database
- [ ] `/add-member <user> [rank] [steam_id]` - Add new members
- [ ] `/modify-member <user>` - Edit member data
- [ ] `/insight <user>` - Show user profile and history
- [ ] `/assimilate` - Bulk import all citizens to database
- [ ] `/ranks` - Display rank hierarchy and requirements overview

### Document Generation

- [ ] `/passport` commands - Generate, view, and update digital passports
- [ ] `/visa` and `/permit` commands - Issue entry permits and special documents
- [ ] `/documents list <user>` - Show all documents for a member
- **Note:** Images saved to database for checkpoint minigame integration

### Moderation

- [ ] `/reprimand <user> <reason>` - Log disciplinary actions
- [ ] `/loa` commands - Submit, approve, and manage leave of absence requests
- **Note:** Approve/deny should use reaction buttons (✅/❌) for better UX

### Configuration

- [ ] `/config ids` - Manage server/channel/role IDs
- [ ] `/settings` - Update bot settings

### Setup & Initialization

- [ ] `/setup roles` - Create and configure default AFDF roles
- [ ] `/setup channels` - Create required channels (announcements, logs, etc.)
- [ ] `/setup permissions` - Configure bot and role permissions
- [ ] `/setup welcome` - Configure welcome messages and auto-roles

## 🔧 Technical Tasks

### Database

- [ ] Steam ID integration and validation
- [ ] Add database indexes for performance
- [ ] Implement proper connection pooling

### Bot Features

- [ ] Auto-role assignment for new members
- [ ] Command audit logging
- [ ] Permission system for sensitive commands
- [ ] Error handling improvements

## 💡 Future Ideas

- [ ] **Music Player (Lavalink)** 🎵
  - [ ] YouTube support
  - [ ] Spotify support (tracks, albums, playlists)
  - [ ] SoundCloud support
  - [ ] Advanced queue management
  - [ ] Volume controls and now playing info
- [ ] Statistics dashboard
- [ ] Web admin interface
- [ ] Steam Workshop integration

## 🎮 Minigames & Interactive Features

- [ ] **Papers Please Style Border Checkpoint Minigame** 🛂
  - [ ] `/checkpoint start/status/leaderboard/rules` - Core checkpoint commands
  - [ ] Document verification system (passports, visas, permits, certificates)
  - [ ] Interactive decisions (approve/deny/detain/confiscate)
  - [ ] Scoring system with performance tracking
  - [ ] Random events (smuggling, fake docs, VIPs, emergencies)
  - [ ] Economic simulation (salary, expenses, upgrades)
  - [ ] Progressive difficulty and story mode
  - [ ] Multiplayer cooperative shifts and competitions
- [ ] **Smuggling Minigame** 📦
  - [ ] `/smuggle` commands - Attempt to move contraband across borders
  - [ ] Risk/reward system with detection chances
  - [ ] Underground network and reputation system
  - [ ] Counter-smuggling operations for border officers

---

**Last updated:** August 16, 2025