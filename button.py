import RPi.GPIO as GPIO
import subprocess

BUTTON_PIN = 21

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def button_callback(channel):
    subprocess.call(["systemctl", "start", "nametag.service"])

GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=button_callback, bouncetime=300)

try:
    while True:
        pass
except KeyboardInterrupt:
    GPIO.cleanup()
