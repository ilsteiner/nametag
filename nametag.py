#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
from datetime import datetime
import logging
from waveshare_epd import epd5in65f
from PIL import Image, ImageDraw, ImageFont
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

logging.basicConfig(level=logging.DEBUG)

# Make sure all required weather variables are listed here
url = "https://api.open-meteo.com/v1/forecast"
params = {
	"latitude": 52.52,
	"longitude": 13.41,
	"daily": ["weather_code", "temperature_2m_max", "temperature_2m_min", "sunrise", "sunset", "precipitation_probability_max"],
	"temperature_unit": "fahrenheit",
	"wind_speed_unit": "mph",
	"precipitation_unit": "inch",
    "timeformat": "unixtime",
	"timezone": "America/Los_Angeles",
    "forecast_days": 2
}
responses = openmeteo.weather_api(url, params=params)

response = responses[0]

# Process daily data for today and tomorrow
daily = response.Daily()
daily_weather_code = daily.Variables(0).ValuesAsNumpy()  # Weather codes for icons
daily_temperature_2m_max = daily.Variables(1).ValuesAsNumpy()  # Max temps
daily_temperature_2m_min = daily.Variables(2).ValuesAsNumpy()  # Min temps
daily_sunrise = daily.Variables(3).ValuesAsNumpy() # Sunrise
daily_sunset = daily.Variables(4).ValuesAsNumpy() # Sunset
daily_precipitation_probability = daily.Variables(5).ValuesAsNumpy()  # Precipitation probabilities

daily_data = {"date": pd.date_range(
	start = pd.to_datetime(daily.Time(), unit = "s", utc = True),
	end = pd.to_datetime(daily.TimeEnd(), unit = "s", utc = True),
	freq = pd.Timedelta(seconds = daily.Interval()),
	inclusive = "left"
)}
daily_data["weather_code"] = daily_weather_code
daily_data["temp_high"] = daily_temperature_2m_max
daily_data["temp_low"] = daily_temperature_2m_min
daily_data["sunrise"] = daily_sunrise
daily_data["sunset"] = daily_sunset
daily_data["precip"] = daily_precipitation_probability

weather_dataframe = pd.DataFrame(data = daily_data)

logging.info(weather_dataframe)

# Extract today's and tomorrow's data using iloc
today_max = weather_dataframe.iloc[0]["temp_high"]
today_min = weather_dataframe.iloc[0]["temp_low"]
today_precip_prob = weather_dataframe.iloc[0]["precip"]
today_weather_code = weather_dataframe.iloc[0]["weather_code"]
today_sunrise = weather_dataframe.iloc[0]['sunrise']
today_sunset = weather_dataframe.iloc[0]["sunset"]

tomorrow_max = weather_dataframe.iloc[1]["temp_high"]
tomorrow_min = weather_dataframe.iloc[1]["temp_low"]
tomorrow_precip_prob = weather_dataframe.iloc[1]["precip"]
tomorrow_weather_code = weather_dataframe.iloc[1]["weather_code"]
tomorrow_sunrise = weather_dataframe.iloc[1]['sunrise']
tomorrow_sunset = weather_dataframe.iloc[1]["sunset"]

def get_weather_icon_path(weather_code, is_night=False):
    day_icons = {
        0: "icons/PNG/512/day_clear.png",                           # Clear sky
        1: "icons/PNG/512/day_partial_cloud.png",                   # Mainly clear
        2: "icons/PNG/512/cloudy.png",                              # Partly cloudy
        3: "icons/PNG/512/overcast.png",                            # Overcast
        45: "icons/PNG/512/fog.png",                                # Fog
        51: "icons/PNG/512/mist.png",                               # Mist
        61: "icons/PNG/512/rain.png",                               # Rain
        71: "icons/PNG/512/snow.png",                               # Snow
        95: "icons/PNG/512/thunder.png",                            # Thunderstorm
    }

    night_icons = {
        0: "icons/PNG/512/night_half_moon_clear.png",               # Clear night
        1: "icons/PNG/512/night_half_moon_partial_cloud.png",       # Partially cloudy night
        2: "icons/PNG/512/cloudy.png",                              # Partly cloudy night
        3: "icons/PNG/512/overcast.png",                            # Overcast night
        45: "icons/PNG/512/fog.png",                                # Fog at night
        51: "icons/PNG/512/mist.png",                               # Mist at night
        61: "icons/PNG/512/night_half_moon_rain.png",               # Rain at night
        71: "icons/PNG/512/night_half_moon_snow.png",               # Snow at night
        95: "icons/PNG/512/thunder.png",                            # Thunderstorm at night
    }

    if is_night:
        return night_icons.get(weather_code, "icons/PNG/512/unknown.png")  # Default icon if code is unknown
    else:
        return day_icons.get(weather_code, "icons/PNG/512/unknown.png")    # Default icon if code is unknown

# Determine if it's night based on the current time and sunset time
current_time = datetime.now()
logging.info("Sunset: " + str(today_sunset))
sunset_time = datetime.fromtimestamp(today_sunset)

is_night = str(sunset_time) != "0" and current_time > sunset_time

# Get appropriate icons for today and tomorrow
weather_icon_today_path = get_weather_icon_path(today_weather_code, is_night)
weather_icon_tomorrow_path = get_weather_icon_path(tomorrow_weather_code, False)  # Assume tomorrow is daytime

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
        font_tiny = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
        # font_emoji = ImageFont.truetype('/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf', 75)
        # font_emoji2 = ImageFont.truetype('/usr/share/fonts/truetype/font-awesome/fontawesome-webfont.ttf', 75)
    except IOError:
        print("Font file not found. Using default.")
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_tiny = ImageFont.load_default()
        # font_emoji = ImageFont.load_default()
        # font_emoji2 = ImageFont.load_default()

    # Text strings
    greeting = "I'm"
    name = "Isaac!"
    pronouns = "he/him"

    # Calculate text sizes
    greeting_bbox = draw.textbbox((0, 0), greeting, font=font_large)
    greeting_width, greeting_height = greeting_bbox[2] - greeting_bbox[0], greeting_bbox[3] - greeting_bbox[1]

    name_bbox = draw.textbbox((0, 0), name, font=font_large)
    name_width, name_height = name_bbox[2] - name_bbox[0], name_bbox[3] - name_bbox[1]

    pronouns_bbox = draw.textbbox((0, 0), pronouns, font=font_small)
    pronouns_width, pronouns_height = pronouns_bbox[2] - pronouns_bbox[0], pronouns_bbox[3] - pronouns_bbox[1]

    # Calculate positions for greeting and pronouns
    margin = 20
    padding = 30

    # Row 1 (Greeting + Name)
    row1x = margin
    row1y = margin
    greeting_coord = (row1x, row1y)
    name_coord = (row1x + greeting_width + padding, row1y)

    # Row 2 (Pronouns)
    row2x = margin
    row2y = row1y + greeting_height + padding
    pronouns_coord = (row2x, row2y)

    # Row 3 (Weather Forecast - Today and Tomorrow)
    row3x = margin
    row3y = row2y + pronouns_height + padding

    # Draw greeting, name, pronouns
    draw.text(greeting_coord, greeting, font=font_large, fill=(0, 0, 0))
    draw.text(name_coord, name, font=font_large, fill=(255, 0, 0))  # Red text for name
    draw.text(pronouns_coord, pronouns, font=font_small, fill=(0, 0, 0))

        # Row 3 (Weather Forecast - Today and Tomorrow)
    row3y = row2y + pronouns_height + 2 * padding
    block_width = (epd.width - 3 * margin) // 2  # Divide the width into two blocks with a margin in between
    block_height = epd.height - row3y - margin  # Adjust height to fit within the screen, considering margin

    # Today's Forecast Block
    today_block_x = margin
    today_block_y = row3y

    # Tomorrow's Forecast Block
    tomorrow_block_x = today_block_x + block_width + margin
    tomorrow_block_y = today_block_y

    # Load and paste weather icons for today and tomorrow
    try:
        today_icon = Image.open(weather_icon_today_path)
        tomorrow_icon = Image.open(weather_icon_tomorrow_path)

        # Resize icons to fit within the forecast block
        icon_size = (75, 75)
        today_icon = today_icon.resize(icon_size)
        tomorrow_icon = tomorrow_icon.resize(icon_size)

        # Paste icons into image
        image.paste(today_icon, (today_block_x + padding, today_block_y + padding))
        image.paste(tomorrow_icon, (tomorrow_block_x + padding, tomorrow_block_y + padding))

    except IOError as e:
        print(f"Could not load icon: {e}")

    # Draw forecast texts
    draw.text((today_block_x + padding, today_block_y + icon_size[1] + 2 * padding), f"Max: {today_max:.1f}°F", font=font_tiny, fill=(0, 0, 0))
    draw.text((today_block_x + padding, today_block_y + icon_size[1] + 3 * padding), f"Min: {today_min:.1f}°F", font=font_tiny, fill=(0, 0, 0))
    draw.text((today_block_x + padding, today_block_y + icon_size[1] + 4 * padding), f"Precip: {today_precip_prob:.0f}%", font=font_tiny, fill=(0, 0, 0))

    draw.text((tomorrow_block_x + padding, tomorrow_block_y + icon_size[1] + 2 * padding), f"Max: {tomorrow_max:.1f}°F", font=font_tiny, fill=(0, 0, 0))
    draw.text((tomorrow_block_x + padding, tomorrow_block_y + icon_size[1] + 3 * padding), f"Min: {tomorrow_min:.1f}°F", font=font_tiny, fill=(0, 0, 0))
    draw.text((tomorrow_block_x + padding, tomorrow_block_y + icon_size[1] + 4 * padding), f"Precip: {tomorrow_precip_prob:.0f}%", font=font_tiny, fill=(0, 0, 0))

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
