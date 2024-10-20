#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
import logging
from waveshare_epd import epd5in65f
from PIL import Image, ImageDraw, ImageFont
import openmeteo_requests
import requests_cache
from retry_requests import retry

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# Make sure all required weather variables are listed here
url = "https://api.open-meteo.com/v1/forecast"
params = {
	"latitude": 52.52,
	"longitude": 13.41,
	"daily": ["weather_code", "temperature_2m_max", "temperature_2m_min", "sunrise", "sunset", "precipitation_probability_max"],
	"temperature_unit": "fahrenheit",
	"wind_speed_unit": "mph",
	"precipitation_unit": "inch",
	"timezone": "America/Los_Angeles"
}
responses = openmeteo.weather_api(url, params=params)

response = responses[0]

# Process daily data for today and tomorrow
daily = response.Daily()
daily_weather_code = daily.Variables(0).ValuesAsNumpy()  # Weather codes for icons
daily_temperature_2m_max = daily.Variables(1).ValuesAsNumpy()  # Max temps
daily_temperature_2m_min = daily.Variables(2).ValuesAsNumpy()  # Min temps
sunrise = daily.Variables(3).ValuesAsNumpy() # Sunrise
sunset = daily.Variables(4).ValuesAsNumpy() # Sunset
daily_precipitation_probability = daily.Variables(5).ValuesAsNumpy()  # Precipitation probabilities

# Extract today's and tomorrow's data
today_max = daily_temperature_2m_max[0]
today_min = daily_temperature_2m_min[0]
today_precip_prob = daily_precipitation_probability[0]
today_weather_code = daily_weather_code[0]

tomorrow_max = daily_temperature_2m_max[1]
tomorrow_min = daily_temperature_2m_min[1]
tomorrow_precip_prob = daily_precipitation_probability[1]
tomorrow_weather_code = daily_weather_code[1]

# Function to map weather code to an icon representation
def get_weather_icon(weather_code):
    icons = {
        0: "☀️",  # Clear sky
        1: "🌤️",  # Mainly clear
        2: "⛅",   # Partly cloudy
        3: "☁️",  # Overcast
        45: "🌫️",  # Fog
        51: "🌦️",  # Drizzle
        61: "🌧️",  # Rain
        71: "❄️",  # Snow
        95: "⛈️",  # Thunderstorm
    }
    return icons.get(weather_code, "❓")  # Default icon if code is unknown

# Weather icons for today and tomorrow
weather_icon_today = get_weather_icon(today_weather_code)
weather_icon_tomorrow = get_weather_icon(tomorrow_weather_code)

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
        font_tiny = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
    except IOError:
        print("Font file not found. Using default.")
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

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

    today_coord = (row3x, row3y)
    today_text = f"Today: {weather_icon_today} Max: {today_max:.1f}°F Min: {today_min:.1f}°F Precip: {today_precip_prob:.0f}%"

    tomorrow_coord = (row3x, row3y + 60)  # 60 pixels below today's forecast
    tomorrow_text = f"Tomorrow: {weather_icon_tomorrow} Max: {tomorrow_max:.1f}°F Min: {tomorrow_min:.1f}°F Precip: {tomorrow_precip_prob:.0f}%"

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

    # Draw Today Block
    draw.rectangle(
        (today_block_x, today_block_y, today_block_x + block_width, today_block_y + block_height),
        outline=(0, 0, 0),
        width=3
    )
    draw.text((today_block_x + padding, today_block_y + padding), "Today", font=font_small, fill=(0, 0, 0))
    draw.text((today_block_x + padding, today_block_y + font_small.size + 2 * padding), f"{weather_icon_today}", font=font_large, fill=(0, 0, 0))
    draw.text((today_block_x + padding, today_block_y + font_small.size + 3 * padding + font_large.size), f"Max: {today_max:.1f}°F", font=font_tiny, fill=(0, 0, 0))
    draw.text((today_block_x + padding, today_block_y + font_small.size + 4 * padding + font_large.size), f"Min: {today_min:.1f}°F", font=font_tiny, fill=(0, 0, 0))
    draw.text((today_block_x + padding, today_block_y + font_small.size + 5 * padding + font_large.size), f"Precip: {today_precip_prob:.0f}%", font=font_tiny, fill=(0, 0, 0))

    # Draw Tomorrow Block
    draw.rectangle(
        (tomorrow_block_x, tomorrow_block_y, tomorrow_block_x + block_width, tomorrow_block_y + block_height),
        outline=(0, 0, 0),
        width=3
    )
    draw.text((tomorrow_block_x + padding, tomorrow_block_y + padding), "Tomorrow", font=font_small, fill=(0, 0, 0))
    draw.text((tomorrow_block_x + padding, tomorrow_block_y + font_small.size + 2 * padding), f"{weather_icon_tomorrow}", font=font_large, fill=(0, 0, 0))
    draw.text((tomorrow_block_x + padding, tomorrow_block_y + font_small.size + 3 * padding + font_large.size), f"Max: {tomorrow_max:.1f}°F", font=font_tiny, fill=(0, 0, 0))
    draw.text((tomorrow_block_x + padding, tomorrow_block_y + font_small.size + 4 * padding + font_large.size), f"Min: {tomorrow_min:.1f}°F", font=font_tiny, fill=(0, 0, 0))
    draw.text((tomorrow_block_x + padding, tomorrow_block_y + font_small.size + 5 * padding + font_large.size), f"Precip: {tomorrow_precip_prob:.0f}%", font=font_tiny, fill=(0, 0, 0))

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
