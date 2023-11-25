'''
Fetch the shift data from Humanity API to create a report on standby shifts
1. Request the data from API for a given period
2. Convert the response into pandas df
3. Modify the data to list
    - Name, Number of shifts, Total hours, Weekday hours, Weekend hours
    - Account for breaks
4. Export the report to csv
'''

from fastapi import FastAPI

app = FastAPI()

@app.get('/')
async def root():
    return {'message': 'Hello!'}
