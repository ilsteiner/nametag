from gpiozero import Button
from signal import pause
import subprocess

BUTTON_PIN = 21

def button_pressed():
    print("Button pressed! Running the script...")
    subprocess.run(["/home/isaac/nametag/bin/python3", "/home/isaac/nametag/nametag.py"])

button = Button(BUTTON_PIN, pull_up=True)
button.when_pressed = button_pressed

pause()  # Keeps the script running
