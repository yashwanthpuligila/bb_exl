@echo off
echo Installing requirements for Web Invoice Generator...
cd web
pip install -r requirements.txt
echo.
echo Starting Web Invoice Generator...
echo.
echo Open your browser and go to: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.
python app.py
pause