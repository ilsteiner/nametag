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
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 80)  # Font size 80
    except IOError:
        print("Font file not found. Using default.")
        font = ImageFont.load_default()

    # Get the width and height of the text to be drawn
    text = "Hey, I'm Isaac!"
    text_width, text_height = draw.textsize(text, font=font)

    # Center the text in the middle of the e-paper display
    x = (epd.width - text_width) / 2
    y = (epd.height - text_height) / 2

    # Draw the text
    draw.text((x, y), text, font=font, fill=(0, 0, 0))  # Black text

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
