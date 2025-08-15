# Docker Deployment Guide

This project uses Docker Compose with profiles for flexible deployment. You can run the database independently for development or everything together for production.

## 🚀 Quick Start

1. **Copy environment file:**
   
   ```bash
   cp .env.example .env
   ```

2. **Add your Discord token to `.env`:**
   
   ```env
   DISCORD_TOKEN=your_actual_discord_bot_token
   ```

3. **Choose your deployment:**

   **For Development** (Database + Local Bot):
   
   ```bash
   docker-compose --profile database up -d
   python main.py
   ```

   **For Production** (Everything in Docker):
   
   ```bash
   docker-compose --profile full up -d
   ```

## 📋 Available Profiles

| Profile | Services | Use Case |
|---------|----------|----------|
| `database` | PostgreSQL + pgAdmin | Development with local bot |
| `bot` | Discord Bot only | Bot-only deployment |
| `full` | All services | Production deployment |

## 🛠️ Common Commands

### Development Workflow

```bash
# Start database services
docker-compose --profile database up -d

# Access services:
# - PostgreSQL: localhost:5432
# - pgAdmin: http://localhost:5050
#   - Email: federation.aegean@gmail.com
#   - Password: admin

# Run bot locally
python main.py
```

### Production Deployment

```bash
# Start everything
docker-compose --profile full up -d

# View logs
docker-compose logs -f

# Stop everything
docker-compose down
```

### Maintenance

```bash
# Rebuild bot after code changes
docker-compose build bot
docker-compose --profile bot up -d

# Database maintenance (keeps DB running)
docker-compose stop bot
# Use pgAdmin at http://localhost:5050

# Restart specific services
docker-compose restart postgres
docker-compose restart bot
```

## 🔧 Configuration

### Environment Variables

Required in `.env` file:

- `DISCORD_TOKEN` - Your Discord bot token

### Database Connection

- **Host**: `postgres` (from containers) or `localhost` (from host)
- **Port**: `5432`
- **Database**: `AFdb`
- **Username**: `postgres`  
- **Password**: `admin`

### pgAdmin Access

- **URL**: <http://localhost:5050>
- **Email**: `federation.aegean@gmail.com`
- **Password**: admin

## 🐛 Troubleshooting

**Bot won't start:**

- Check if database is healthy: `docker-compose ps`
- Verify Discord token in `.env`

**Can't connect to database:**

- Ensure database profile is running: `docker-compose --profile database ps`
- Check if port 5432 is available

**pgAdmin login issues:**

- Use the credentials above
- Reset with: `docker-compose restart pgadmin`