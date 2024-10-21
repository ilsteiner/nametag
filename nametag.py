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
import math
from datetime import datetime, time

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
	"timezone": "America/Los_Angeles",
    "forecast_days": 2
}
responses = openmeteo.weather_api(url, params=params)

response = responses[0]

# Process daily data for today and tomorrow
daily = response.Daily()
logging.info("Daily" + str(daily))
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

logging.info("Sunrise:" + daily_sunrise)

# Extract today's and tomorrow's data using iloc
today_max = weather_dataframe.iloc[0]["temp_high"]
today_min = weather_dataframe.iloc[0]["temp_low"]
today_precip_prob = weather_dataframe.iloc[0]["precip"]
today_weather_code = weather_dataframe.iloc[0]["weather_code"]
today_sunrise = datetime.fromisoformat(daily_sunrise[0])
today_sunset = datetime.fromisoformat(daily_sunset[0])

tomorrow_max = weather_dataframe.iloc[1]["temp_high"]
tomorrow_min = weather_dataframe.iloc[1]["temp_low"]
tomorrow_precip_prob = weather_dataframe.iloc[1]["precip"]
tomorrow_weather_code = weather_dataframe.iloc[1]["weather_code"]
# tomorrow_sunrise = datetime.fromisoformat(daily_sunrise[1])
# tomorrow_sunset = datetime.fromisoformat(daily_sunset[1])

def get_weather_icon_path(wmo_code, is_night=False):
    if wmo_code == 0:
        return "icons/PNG/512/night_half_moon_clear.png" if is_night else "icons/PNG/512/day_clear.png"
    elif wmo_code == 1:
        return "icons/PNG/512/night_half_moon_partial_cloud.png" if is_night else "icons/PNG/512/day_partial_cloud.png"
    elif wmo_code == 2 or wmo_code == 3:
        return "icons/PNG/512/cloudy.png"
    elif wmo_code == 4:
        return "icons/PNG/512/overcast.png"
    elif 45 <= wmo_code <= 49:
        return "icons/PNG/512/fog.png"
    elif 50 <= wmo_code <= 53:
        return "icons/PNG/512/mist.png"
    elif 54 <= wmo_code <= 56:
        return "icons/PNG/512/mist.png"  # Heavy mist could use the same icon for now
    elif wmo_code == 57:
        return "icons/PNG/512/fog.png"
    elif 60 <= wmo_code <= 63:
        return "icons/PNG/512/rain.png"
    elif 64 <= wmo_code <= 67:
        return "icons/PNG/512/day_rain.png" if not is_night else "icons/PNG/512/night_half_moon_rain.png"
    elif 68 <= wmo_code <= 69:
        return "icons/PNG/512/sleet.png"
    elif 70 <= wmo_code <= 79:
        return "icons/PNG/512/snow.png"
    elif wmo_code == 80:
        return "icons/PNG/512/rain.png"
    elif wmo_code == 81:
        return "icons/PNG/512/rain_thunder.png"
    elif wmo_code == 82:
        return "icons/PNG/512/angry_clouds.png"
    elif 85 <= wmo_code <= 86:
        return "icons/PNG/512/snow_thunder.png"
    elif 95 <= wmo_code <= 99:
        return "icons/PNG/512/thunder.png"
    else:
        return "icons/PNG/512/unknown.png"  # Default icon if code is unknown

# Determine if it's night based on the current time and sunset time
current_time = datetime.now()
fallback_sunset = datetime.combine(datetime.now().date(), time(17, 0))
logging.info("Sunset: " + str(today_sunset))

is_night = current_time > today_sunset or current_time > fallback_sunset

logging.info("Today code: " + str(today_weather_code))
logging.info("Tomorrow code: " + str(tomorrow_weather_code))

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
    background_color = (255,255,255)
    image = Image.new('RGB', (epd.width, epd.height), background_color)  # White background
    draw = ImageDraw.Draw(image)

    try:
        font_large = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 75)
        font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 40)
        font_tiny = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
        font_micro = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
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
    row3y = row2y + pronouns_height + padding
    block_width = (epd.width - 3 * margin) // 2  # Divide the width into two blocks with a margin in between
    block_height = epd.height - row3y - margin  # Adjust height to fit within the screen, considering margin

    # Settings for drop shadow and card
    shadow_offset = 10
    shadow_color = (150, 150, 150)  # Gray for shadow
    card_color = (230, 230, 230)  # Light gray for card
    card_radius = 15

    # Today's Forecast Block with shadow
    today_block_x = margin
    today_block_y = row3y

    draw.rounded_rectangle(
        [today_block_x + shadow_offset, today_block_y + shadow_offset,
        today_block_x + block_width + shadow_offset, today_block_y + block_height + shadow_offset],
        radius=card_radius, fill=shadow_color
    )

    draw.rounded_rectangle(
        [today_block_x, today_block_y,
        today_block_x + block_width, today_block_y + block_height],
        radius=card_radius, fill=card_color
    )

    # Tomorrow's Forecast Block with shadow
    tomorrow_block_x = today_block_x + block_width + margin
    tomorrow_block_y = today_block_y

    draw.rounded_rectangle(
        [tomorrow_block_x + shadow_offset, tomorrow_block_y + shadow_offset,
        tomorrow_block_x + block_width + shadow_offset, tomorrow_block_y + block_height + shadow_offset],
        radius=card_radius, fill=shadow_color
    )

    draw.rounded_rectangle(
        [tomorrow_block_x, tomorrow_block_y,
        tomorrow_block_x + block_width, tomorrow_block_y + block_height],
        radius=card_radius, fill=card_color
    )

    # Label the cards
    today_card_label_text = "Today"
    today_card_label_bbox = draw.textbbox((0, 0), today_card_label_text, font=font_small)
    today_card_label_width, today_card_label_height = today_card_label_bbox[2] - today_card_label_bbox[0], today_card_label_bbox[3] - today_card_label_bbox[1]

    tomorrow_card_label_text = "Tomorrow"
    tomorrow_card_label_bbox = draw.textbbox((0, 0), tomorrow_card_label_text, font=font_small)
    tomorrow_card_label_width, tomorrow_card_label_height = tomorrow_card_label_bbox[2] - tomorrow_card_label_bbox[0], tomorrow_card_label_bbox[3] - tomorrow_card_label_bbox[1]

    draw.text((today_block_x + padding, today_block_y + padding),today_card_label_text,font=font_small,fill=(0,0,0))
    draw.text((tomorrow_block_x + padding, tomorrow_block_y + padding),tomorrow_card_label_text,font=font_small,fill=(0,0,0))

    # Load and paste weather icons for today and tomorrow
    try:
        today_icon = Image.open(weather_icon_today_path).convert("RGBA")
        tomorrow_icon = Image.open(weather_icon_tomorrow_path).convert("RGBA")

        # Resize and fix backgrounds icons to fit within the forecast block
        icon_size = (math.trunc(block_width/2 - margin - padding), math.trunc(block_width/2 - margin - padding))
        icon_background = Image.new("RGBA", icon_size, card_color)

        today_icon = today_icon.resize(icon_size)
        tomorrow_icon = tomorrow_icon.resize(icon_size)

        today_icon = Image.alpha_composite(icon_background, today_icon)
        tomorrow_icon = Image.alpha_composite(icon_background, tomorrow_icon)

        today_icon_y = today_block_y + ((block_height - today_card_label_height - icon_size[0] - padding * 2))
        tomorrow_icon_y = tomorrow_block_y + ((block_height - tomorrow_card_label_height - icon_size[0] - padding * 2))

        # Paste icons into image
        image.paste(today_icon, (today_block_x + padding, math.trunc(tomorrow_icon_y)))
        image.paste(tomorrow_icon, (tomorrow_block_x + padding, math.trunc(tomorrow_icon_y)))

    except IOError as e:
        print(f"Could not load icon: {e}")

    # Draw forecast texts
    draw.text((today_block_x + padding * 2 + icon_size[0], today_icon_y + padding * 1), f"High: {today_max:.1f}°F", font=font_micro, fill=(0, 0, 0))
    draw.text((today_block_x + padding * 2 + icon_size[0], today_icon_y + padding * 2), f"Low: {today_min:.1f}°F", font=font_micro, fill=(0, 0, 0))
    draw.text((today_block_x + padding * 2 + icon_size[0], today_icon_y + padding * 3), f"Precip: {today_precip_prob:.0f}%", font=font_micro, fill=(0, 0, 0))

    draw.text((tomorrow_block_x + padding * 2 + icon_size[0], tomorrow_icon_y + padding * 1), f"High: {tomorrow_max:.1f}°F", font=font_micro, fill=(0, 0, 0))
    draw.text((tomorrow_block_x + padding * 2 + icon_size[0], tomorrow_icon_y + padding * 2), f"Low: {tomorrow_min:.1f}°F", font=font_micro, fill=(0, 0, 0))
    draw.text((tomorrow_block_x + padding * 2 + icon_size[0], tomorrow_icon_y + padding * 3), f"Precip: {tomorrow_precip_prob:.0f}%", font=font_micro, fill=(0, 0, 0))

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
