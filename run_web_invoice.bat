@echo off
cd /d "%~dp0web"
set DATABASE_ENGINE=sqlite
set DATABASE_URL=
set POSTGRES_URL=
set POSTGRESQL_URL=
echo Starting Web Invoice Generator (SQLite Local Engine)...
echo.
echo Open your browser and go to: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.
python app.py
pause