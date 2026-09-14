@echo off
title Sri Laxmi Gayatri Traders - Invoice ERP
cd /d "%~dp0"
set DATABASE_ENGINE=sqlite
set DATABASE_URL=
set POSTGRES_URL=
set POSTGRESQL_URL=
echo Starting Invoice ERP Desktop App (SQLite Local Engine)...
python desktop_app.py

