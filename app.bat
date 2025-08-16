@echo off
REM AFDF Border Bot - Quick Control Script

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="start" goto start
if "%1"=="stop" goto stop
if "%1"=="restart" goto restart
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
echo Usage: ./app [command] [profile]
echo.
echo Commands:
echo   start [profile]   - Start services (database/bot/all)
echo   stop [service]    - Stop services (all/bot/database)
echo   restart [profile] - Restart services  
echo   logs [service]    - View logs (all/bot/postgres/pgadmin)
echo   status           - Show running containers
echo   clean            - Stop everything and remove volumes (WARNING: deletes data!)
echo   help             - Show this help
echo.
echo Short aliases:
echo   up [profile]     - Same as start
echo   down [service]   - Same as stop  
echo   ps               - Same as status
echo   l [service]      - Same as logs
echo.
echo Examples:
echo   ./app start database    - Start database services
echo   ./app start bot         - Start bot services  
echo   ./app start all         - Start all services
echo   ./app stop              - Stop everything (keeps data)
echo   ./app stop bot          - Stop only bot
echo   ./app clean             - Stop and remove ALL data (WARNING!)
echo.
echo Short examples:
echo   ./app up all            - Start all services
echo   ./app down              - Stop everything  
echo   ./app ps                - Show status
echo   ./app l bot             - View bot logs
goto end

:start
echo Ensuring clean state before start...
docker-compose down --remove-orphans 2>nul
timeout /t 2 /nobreak >nul

if "%2"=="" (
    echo Starting all services...
    docker-compose --profile full up -d
) else if "%2"=="all" (
    echo Starting all services...
    docker-compose --profile full up -d
) else (
    echo Starting %2 profile...
    docker-compose --profile %2 up -d
)
goto end

:stop
if "%2"=="" goto stop_all
if "%2"=="all" goto stop_all
if "%2"=="bot" goto stop_bot
if "%2"=="database" goto stop_database
goto stop_all

:stop_all
echo Stopping all services (keeping volumes for data persistence)...
echo Trying docker-compose down...
docker-compose down --remove-orphans --volumes=false
echo Waiting for containers to fully stop...
timeout /t 3 /nobreak >nul
echo Checking for any remaining containers...
for /f "tokens=1" %%i in ('docker ps -q --filter "name=afdfborderbot" 2^>nul') do (
    echo Found remaining container %%i, stopping...
    docker stop %%i
)
echo Cleaning up any stopped containers...
docker container prune -f 2>nul
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
    docker-compose down --remove-orphans --volumes
    echo Cleaning up containers and volumes...
    docker container prune -f 2>nul
    docker volume prune -f 2>nul
    echo Everything cleaned and data deleted.
) else (
    echo Cancelled. No data was deleted.
)
goto end

:end
