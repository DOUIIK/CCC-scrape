@echo off
echo Removing any existing FlareSolverr container...
docker rm -f flaresolverr
echo Starting FlareSolverr container...
docker run -d ^
  --name=flaresolverr ^
  -p 8191:8191 ^
  -e LOG_LEVEL=info ^
  --restart unless-stopped ^
  ghcr.io/flaresolverr/flaresolverr:latest
echo FlareSolverr container started on port 8191.
pause
