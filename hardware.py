import serial
import RPi.GPIO as GPIO
from adafruit_fingerprint import Adafruit_Fingerprint
from escpos.printer import File

# GPIO Pins
BTN_BACK = 17
BTN_NEXT = 27

def setup_hardware():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BTN_BACK, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(BTN_NEXT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    uart = serial.Serial("/dev/serial0", baudrate=57600, timeout=1)
    finger = Adafruit_Fingerprint(uart)
    return finger

def print_tardy_slip(img_rotated):
    p = File("/dev/usb/lp0")
    try:
        p.image(img_rotated)
        p.cut()
    finally:
        p.close()
