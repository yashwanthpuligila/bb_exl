@echo off
set DATABASE_ENGINE=sqlite
set DATABASE_URL=
set POSTGRES_URL=
set POSTGRESQL_URL=
echo Starting Web Invoice Generator Server (SQLite Local Engine)...
cd /d "%~dp0"
python app.py
pause