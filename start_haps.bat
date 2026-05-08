@echo off
echo Starting HAPS Production Server on http://0.0.0.0:5000...
waitress-serve --host=0.0.0.0 --port=5000 app:app
pause
