#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

import logging
from waveshare_epd import epd5in65f
import time
from PIL import Image,ImageDraw,ImageFont
import traceback

import openmeteo_requests

import requests_cache
import pandas as pd
from retry_requests import retry

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

# Make sure all required weather variables are listed here
# The order of variables in hourly or daily is important to assign them correctly below
url = "https://api.open-meteo.com/v1/forecast"
params = {
	"latitude": 52.52,
	"longitude": 13.41,
	"current": ["temperature_2m", "apparent_temperature", "is_day", "precipitation"],
	"hourly": ["temperature_2m", "apparent_temperature", "precipitation_probability", "precipitation"],
	"daily": ["weather_code", "temperature_2m_max", "temperature_2m_min", "apparent_temperature_max", "apparent_temperature_min", "sunrise", "sunset"],
	"temperature_unit": "fahrenheit",
	"wind_speed_unit": "mph",
	"precipitation_unit": "inch",
	"timezone": "America/Los_Angeles",
	"forecast_days": 3
}
responses = openmeteo.weather_api(url, params=params)

response = responses[0]
print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
print(f"Elevation {response.Elevation()} m asl")
print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

# Current values. The order of variables needs to be the same as requested.
current = response.Current()
current_temperature_2m = current.Variables(0).Value()
current_apparent_temperature = current.Variables(1).Value()
current_is_day = current.Variables(2).Value()
current_precipitation = current.Variables(3).Value()

print(f"Current time {current.Time()}")
print(f"Current temperature_2m {current_temperature_2m}")
print(f"Current apparent_temperature {current_apparent_temperature}")
print(f"Current is_day {current_is_day}")
print(f"Current precipitation {current_precipitation}")

# Process hourly data. The order of variables needs to be the same as requested.
hourly = response.Hourly()
hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
hourly_apparent_temperature = hourly.Variables(1).ValuesAsNumpy()
hourly_precipitation_probability = hourly.Variables(2).ValuesAsNumpy()
hourly_precipitation = hourly.Variables(3).ValuesAsNumpy()

hourly_data = {"date": pd.date_range(
	start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
	end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
	freq = pd.Timedelta(seconds = hourly.Interval()),
	inclusive = "left"
)}
hourly_data["temperature_2m"] = hourly_temperature_2m
hourly_data["apparent_temperature"] = hourly_apparent_temperature
hourly_data["precipitation_probability"] = hourly_precipitation_probability
hourly_data["precipitation"] = hourly_precipitation

hourly_dataframe = pd.DataFrame(data = hourly_data)
print(hourly_dataframe)

# Process daily data. The order of variables needs to be the same as requested.
daily = response.Daily()
daily_weather_code = daily.Variables(0).ValuesAsNumpy()
daily_temperature_2m_max = daily.Variables(1).ValuesAsNumpy()
daily_temperature_2m_min = daily.Variables(2).ValuesAsNumpy()
daily_apparent_temperature_max = daily.Variables(3).ValuesAsNumpy()
daily_apparent_temperature_min = daily.Variables(4).ValuesAsNumpy()
daily_sunrise = daily.Variables(5).ValuesAsNumpy()
daily_sunset = daily.Variables(6).ValuesAsNumpy()

daily_data = {"date": pd.date_range(
	start = pd.to_datetime(daily.Time(), unit = "s", utc = True),
	end = pd.to_datetime(daily.TimeEnd(), unit = "s", utc = True),
	freq = pd.Timedelta(seconds = daily.Interval()),
	inclusive = "left"
)}
daily_data["weather_code"] = daily_weather_code
daily_data["temperature_2m_max"] = daily_temperature_2m_max
daily_data["temperature_2m_min"] = daily_temperature_2m_min
daily_data["apparent_temperature_max"] = daily_apparent_temperature_max
daily_data["apparent_temperature_min"] = daily_apparent_temperature_min
daily_data["sunrise"] = daily_sunrise
daily_data["sunset"] = daily_sunset

daily_dataframe = pd.DataFrame(data = daily_data)
print(daily_dataframe)

logging.basicConfig(level=logging.DEBUG)

try:
    logging.info("Nametag start")
    
    epd = epd5in65f.EPD()
    logging.info("init and Clear")
    epd.init()
    epd.Clear()
    
    # Drawing on the Horizontal image
    logging.info("1.Drawing the image...")
    
    # Create an image to draw on
    image = Image.new('RGB', (epd.width, epd.height), (255, 255, 255))  # White background
    draw = ImageDraw.Draw(image)

    try:
        font_large = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 80)
        font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 40)
    except IOError:
        print("Font file not found. Using default.")
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Text strings
    greeting = "Hey, I'm"
    name = "Isaac!"
    pronouns = "he/him"
    temperature = f"Temp: {current_temperature_2m:.1f}°F"

    # Calculate text sizes
    # Calculate text sizes using textbbox
    greeting_bbox = draw.textbbox((0, 0), greeting, font=font_large)
    greeting_width, greeting_height = greeting_bbox[2] - greeting_bbox[0], greeting_bbox[3] - greeting_bbox[1]

    name_bbox = draw.textbbox((0, 0), name, font=font_large)
    name_width, name_height = name_bbox[2] - name_bbox[0], name_bbox[3] - name_bbox[1]

    pronouns_bbox = draw.textbbox((0, 0), pronouns, font=font_small)
    pronouns_width, pronouns_height = pronouns_bbox[2] - pronouns_bbox[0], pronouns_bbox[3] - pronouns_bbox[1]

    temperature_bbox = draw.textbbox((0, 0), temperature, font=font_small)
    temperature_width, temperature_height = temperature_bbox[2] - temperature_bbox[0], temperature_bbox[3] - temperature_bbox[1]


    # Calculate total height for centered positioning
    total_height = greeting_height + pronouns_height + temperature_height + 60  # 60 pixels padding between lines

    # Calculate starting position to center text
    x_greeting = (epd.width - greeting_width) / 2
    x_name = (epd.width - name_width) / 2
    y = (epd.height - total_height) / 2

    # Draw text centered
    draw.text((x_greeting, y), greeting, font=font_large, fill=(0, 0, 0))  # Black text for greeting
    draw.text((x_name, y + greeting_height), name, font=font_large, fill=(255, 0, 0))  # Red text for name
    draw.text((x_greeting, y + greeting_height + name_height + 20), pronouns, font=font_small, fill=(0, 0, 0))
    draw.text((x_greeting, y + greeting_height + name_height + pronouns_height + 40), temperature, font=font_small, fill=(0, 0, 0))

    # Display the image on the e-paper
    epd.display(epd.getbuffer(image))

    # Put the display to sleep to save power
    epd.sleep()
    
except IOError as e:
    logging.info(e)
    
except KeyboardInterrupt:    
    logging.info("ctrl + c:")
    epd5in65f.epdconfig.module_exit(cleanup=True)
    exit()
