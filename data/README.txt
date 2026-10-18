HISTORICAL RAINFALL DATA

1. Download the rainfall CSV you selected from data.gov.in or another official source.
2. Save a copy here with this exact filename: rainfall.csv
3. Start the app and visit http://127.0.0.1:8000/api/history
4. The endpoint attempts to identify a column containing "year" and a column containing
   "rainfall" or "precipitation". Dataset formats differ; if detection fails, the API returns
   the actual column names so you can map them in app.py.

Dataset source: https://data.gov.in/catalog/rainfall-india
IMD gridded rainfall data: https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html
