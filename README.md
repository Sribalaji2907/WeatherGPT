# WeatherGPT — working starter project

This project keeps the supplied multilingual WeatherGPT HTML interface and connects it to a Python API.

## What works
- Live current conditions and a 7-day forecast for a searched city using Open-Meteo.
- Temperature, apparent temperature, humidity, wind, rain probability/precipitation, UV (where returned), and weather descriptions.
- A next-calendar-month seasonal outlook button using Open-Meteo's seasonal endpoint. It summarizes returned daily values and is explicitly an uncertain model outlook.
- Rule-based chat responses based on the live data currently loaded.
- API endpoint for a historical rainfall CSV downloaded from data.gov.in/IMD (`/api/history`).
- Existing English/Tamil/Hindi/Telugu/Malayalam/Kannada UI selector remains in the HTML.

## Run in VS Code (Windows)
1. Extract the ZIP and open the `WeatherGPT_Working_Project` folder in VS Code.
2. Install Python 3.10 or newer.
3. Open Terminal → New Terminal and run:

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python -m uvicorn app:app --reload
   ```

   If PowerShell blocks activation, use `python -m pip install -r requirements.txt` without activating the environment, or activate from Command Prompt with `.venv\Scripts\activate.bat`.
4. Open http://127.0.0.1:8000 in your browser. Do not open `static/index.html` directly; the frontend calls the backend API.
5. Test backend health at http://127.0.0.1:8000/api/health and interactive API docs at http://127.0.0.1:8000/docs.

## Connect the historical dataset
1. Download a CSV from https://data.gov.in/catalog/rainfall-india (or use a suitable IMD rainfall dataset that you can convert to CSV).
2. Copy it to `data/rainfall.csv`.
3. Open http://127.0.0.1:8000/api/history. The endpoint tries to detect year and rainfall columns. If it cannot, it returns the detected CSV headers; edit the column matching logic in `app.py` to fit the exact file you downloaded.

## Important scientific limitations
- The 7-day forecast is supplied by the weather API; it is not trained from the rainfall CSV.
- The next-month view is a seasonal model outlook, not a precise daily forecast. Seasonal forecasts are uncertain and may not resolve local conditions accurately.
- A rainfall-only historical dataset cannot train reliable temperature, humidity and wind predictions by itself. For a true ML model, collect historical records for all target variables, use time-based train/test validation, compare against a baseline, and display model error metrics.
- The current chat assistant is rule-based, not a large language model. The map panel remains illustrative; live map tiles are not connected.
- Open-Meteo documentation and limitations: https://open-meteo.com/en/docs/forecast-api and https://open-meteo.com/en/docs/seasonal-forecast-api
