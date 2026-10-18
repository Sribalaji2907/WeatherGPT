# WeatherGPT — working starter project

This project keeps the supplied multilingual WeatherGPT HTML interface and connects it to a Python API.

## What works
- Live current conditions and a 7-day forecast for a searched city using Open-Meteo.
- Temperature, apparent temperature, humidity, wind, rain probability/precipitation, UV (where returned), and weather descriptions.
- A next-calendar-month seasonal outlook button using Open-Meteo's seasonal endpoint. It summarizes returned daily values and is explicitly an uncertain model outlook.
- Rule-based chat responses based on the live data currently loaded.

- Existing English/Tamil/Hindi/Telugu/Malayalam/Kannada UI selector remains in the HTML.
