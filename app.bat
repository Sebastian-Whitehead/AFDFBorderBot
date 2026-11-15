@echo off
REM AFDF Border Bot - Quick Control Script

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="start" goto start
if "%1"=="stop" goto stop
if "%1"=="restart" goto restart
if "%1"=="rebuild" goto rebuild
if "%1"=="logs" goto logs
if "%1"=="status" goto status
if "%1"=="clean" goto clean
REM Short aliases
if "%1"=="up" goto start
if "%1"=="down" goto stop
if "%1"=="ps" goto status
if "%1"=="l" goto logs

:help
echo AFDF Border Bot Quick Control
echo.
echo Usage: app [command] [profile]
echo.
echo Commands:
echo   start [profile]   - Start services (database/bot/all; default all)
echo   stop [service]    - Stop services (all/bot/database)
echo   restart [profile] - Restart services  
echo   rebuild [service] - Rebuild and restart services (all/bot)
echo   logs [service]    - View logs (all/bot/postgres/pgadmin)
echo   status           - Show running containers
echo   clean            - Stop everything and remove this project's volumes (WARNING: deletes data!)
echo   help             - Show this help
echo.
echo Short aliases:
echo   up [profile]     - Same as start
echo   down [service]   - Same as stop  
echo   ps               - Same as status
echo   l [service]      - Same as logs
echo.
echo Examples:
echo   app start database    - Start database services
echo   app start bot         - Start bot services  
echo   app start all         - Start all services
echo   app stop              - Stop everything (keeps data)
echo   app stop bot          - Stop only bot
echo   app rebuild bot       - Rebuild and restart bot with latest code
echo   app rebuild all       - Rebuild all services
echo   app clean             - Stop and remove ALL data (WARNING!)
echo.
echo Short examples:
echo   app up all            - Start all services
echo   app down              - Stop everything  
echo   app ps                - Show status
echo   app l bot             - View bot logs
goto end

:start
if "%2"=="" (
    echo Starting all services...
    docker-compose --profile full up -d --remove-orphans
) else if "%2"=="all" (
    echo Starting all services...
    docker-compose --profile full up -d --remove-orphans
) else (
    echo Starting %2 profile...
    docker-compose --profile %2 up -d --remove-orphans
)
goto end

:stop
if "%2"=="" goto stop_all
if "%2"=="all" goto stop_all
if "%2"=="bot" goto stop_bot
if "%2"=="database" goto stop_database
goto stop_all

:stop_all
echo Stopping all services (volumes are kept)...
docker-compose --profile full down --remove-orphans
echo All services stopped (volumes preserved).
goto end

:stop_bot
echo Stopping bot service...
docker-compose stop bot
goto end

:stop_database
echo Stopping database services...
docker-compose stop postgres pgadmin
goto end

:restart
if "%2"=="" (
    echo Restarting all services...
    docker-compose restart
) else (
    echo Restarting %2...
    docker-compose restart %2
)
goto end

:rebuild
if "%2"=="" goto rebuild_all
if "%2"=="all" goto rebuild_all
if "%2"=="bot" goto rebuild_bot
goto rebuild_all

:rebuild_all
echo Rebuilding all services with latest code...
echo Step 1: Stopping services...
docker-compose --profile full down --remove-orphans
echo Step 2: Rebuilding images with no cache...
docker-compose build --no-cache
echo Step 3: Starting all services...
docker-compose --profile full up -d --remove-orphans
echo All services rebuilt and started!
goto end

:rebuild_bot
echo Rebuilding bot service with latest code...
echo Step 1: Stopping bot...
docker-compose stop bot
echo Step 2: Rebuilding bot image with no cache...
docker-compose build --no-cache bot
echo Step 3: Starting bot...
docker-compose up -d bot
echo Bot rebuilt and started!
goto end

:logs
if "%2"=="" (
    echo Showing all logs...
    docker-compose logs -f
) else (
    echo Showing %2 logs...
    docker-compose logs -f %2
)
goto end

:status
echo Current container status:
docker-compose ps
echo.
echo All Docker containers:
docker ps
goto end

:clean
echo WARNING: This will delete all data including database!
set /p confirm="Are you sure? Type 'yes' to continue: "
if /i "%confirm%"=="yes" (
    echo Stopping all services and removing volumes...
    docker-compose --profile full down --remove-orphans --volumes
    echo Everything cleaned and data deleted.
) else (
    echo Cancelled. No data was deleted.
)
goto end

:end
