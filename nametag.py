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
from PIL import Image, ImageDraw, ImageFont
import traceback

import openmeteo_requests

import requests_cache
import pandas as pd
from retry_requests import retry

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

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

# Current values
current = response.Current()
current_temperature_2m = current.Variables(0).Value()

# Process daily data
daily = response.Daily()
daily_temperature_2m_max = daily.Variables(1).ValuesAsNumpy()[0]
daily_temperature_2m_min = daily.Variables(2).ValuesAsNumpy()[0]
daily_weather_code = daily.Variables(0).ValuesAsNumpy()[0]

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
        font_large = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 75)
        font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 40)
    except IOError:
        print("Font file not found. Using default.")
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Text strings
    greeting = "I'm"
    name = "Isaac!"
    pronouns = "he/him"
    temperature = f"Temp: {current_temperature_2m:.1f}°F"
    weather_forecast = f"Max: {daily_temperature_2m_max:.1f}°F, Min: {daily_temperature_2m_min:.1f}°F"

    # Calculate text sizes
    greeting_bbox = draw.textbbox((0, 0), greeting, font=font_large)
    greeting_width, greeting_height = greeting_bbox[2] - greeting_bbox[0], greeting_bbox[3] - greeting_bbox[1]

    name_bbox = draw.textbbox((0, 0), name, font=font_large)
    name_width, name_height = name_bbox[2] - name_bbox[0], name_bbox[3] - name_bbox[1]

    pronouns_bbox = draw.textbbox((0, 0), pronouns, font=font_small)
    pronouns_width, pronouns_height = pronouns_bbox[2] - pronouns_bbox[0], pronouns_bbox[3] - pronouns_bbox[1]

    temperature_bbox = draw.textbbox((0, 0), temperature, font=font_small)
    temperature_width, temperature_height = temperature_bbox[2] - temperature_bbox[0], temperature_bbox[3] - temperature_bbox[1]

    weather_bbox = draw.textbbox((0, 0), weather_forecast, font=font_small)
    weather_width, weather_height = weather_bbox[2] - weather_bbox[0], weather_bbox[3] - weather_bbox[1]

    # Calculate positions
    margin = 20
    padding = 10

    # Row 1
    row1x = margin
    row1y = margin
    greeting_coord = (row1x, row1y)
    name_coord = (row1x + greeting_width + padding, row1y)

    # Row 2
    row2x = margin
    row2y = row1y + padding
    pronouns_coord = (row2x, row2y)

    # Row 3
    row3x = margin
    row3y = row2y + padding
    row3_height = epd.height - row3y

    # Draw name and pronouns
    
    draw.text(greeting_coord, greeting, font=font_large, fill=(0, 0, 0))
    draw.text(name_coord, name, font=font_large, fill=(255, 0, 0))  # Red text for name
    draw.text(pronouns_coord, pronouns, font=font_small, fill=(0, 0, 0))

    # Draw the weather forecast
    seperator_line_width = 2
    weather_block_width = epd.width/2 - seperator_line_width/2 - margin
    weather_block_height = row3_height - margin - padding

    weather_today_coord = (row3x, row3y)
    weather_tomorrow_coord = (row3x + weather_block_width, row3y)

    # Weather today
    draw.text(weather_today_coord, "Today", font=font_small, fill=(0,0,0))

    # Weather tomorrow
    draw.text(weather_tomorrow_coord, "Tomorrow", font=font_small, fill=(0,0,0))


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
