import time
import RPi.GPIO as GPIO
import os
import threading
import queue
import struct
import select

from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas

from escpos.printer import File

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from evdev import InputDevice, categorize, ecodes


# ================= CONFIG =================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RFID_PATH = "/dev/input/event4"
REMOTE_PATH = "/dev/input/by-id/usb-3151_Wireless_Device_b120300001-event-kbd"
PRINTER_PATH = "/dev/usb/lp0"

BUZZER = 22
TIMEOUT_LIMIT = 10  # Seconds of inactivity before home screen

# Remote Scancodes
REMOTE_KEYS_TOGGLE = [109, 104]
REMOTE_KEYS_ENTER = [48, 28, 96]
REMOTE_KEYS_CANCEL = [1, 14]


# ================= HARDWARE INIT =================

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(BUZZER, GPIO.OUT)

NEXT_BUTTON = 17
OK_BUTTON = 27

GPIO.setup(NEXT_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(OK_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def button_pressed(pin):
    return GPIO.input(pin) == 0  # Active low


serial_i2c = i2c(port=1, address=0x3C)
device = ssd1306(serial_i2c, rotate=2)

try:
    font_large = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14
    )
    font_small = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10
    )
except:
    font_large = ImageFont.load_default()
    font_small = ImageFont.load_default()


# ================= HELPERS =================

def get_path(filename):
    return os.path.join(BASE_DIR, filename)


def beep(d=0.1):
    GPIO.output(BUZZER, 1)
    time.sleep(d)
    GPIO.output(BUZZER, 0)


def flush_input(f):
    while True:
        r, _, _ = select.select([f], [], [], 0.001)
        if r:
            f.read(64)
        else:
            break


def oled_msg(text, subtext=""):
    with canvas(device) as draw:
        draw.text((5, 15), str(text).upper(), fill=255, font=font_large)
        if subtext:
            draw.text((5, 35), str(subtext).upper(), fill=255, font=font_small)


def show_home_screen():
    with canvas(device) as draw:
        try:
            logo = Image.open(get_path("logo.png")).convert("1")
            logo.thumbnail((55, 55))
            draw.bitmap((2, 4), logo, fill=255)
        except:
            draw.text((5, 25), "[LOGO]", fill=255, font=font_small)

        draw.text((65, 18), "FRONT", fill=255, font=font_large)
        draw.text((65, 35), "OFFICE", fill=255, font=font_large)


# ================= PRINTER =================

def print_tardy(student, absence):

    if absence.lower() == "neither":
        return True

    now = datetime.now()

    time_str = now.strftime("%I:%M").lstrip("0")
    is_am = now.strftime("%p") == "AM"

    try:
        img = Image.open(get_path("tardy_slip.png")).convert("1")
        draw = ImageDraw.Draw(img)

        f_slip = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24
        )

        draw.text((100, 75), student["name"], font=f_slip, fill=0)
        draw.text((455, 75), student["grade"], font=f_slip, fill=0)

        draw.text((100, 135), now.strftime("%m/%d/%Y"), font=f_slip, fill=0)

        draw.text((385, 135), time_str, font=f_slip, fill=0)

        line_y = 140 if is_am else 160
        draw.line((460, line_y, 490, line_y), fill=0, width=4)

        y_check = 320 if absence.lower() == "excused" else 340
        draw.text((25, y_check), "✓", font=f_slip, fill=0)

        img_rotated = img.rotate(90, expand=True).resize((580, 800))

        p = File(PRINTER_PATH)

        try:
            p.image(img_rotated)
            p.cut()
        finally:
            p.close()

        return True

    except Exception as e:
        print(f"Printing failed: {e}")
        return False


# ================= INPUTS =================

card_queue = queue.Queue()


def rfid_reader_thread():

    try:
        reader = InputDevice(RFID_PATH)

        container = ""

        for event in reader.read_loop():

            if event.type == ecodes.EV_KEY:

                data = categorize(event)

                if data.keystate == 1:

                    if data.keycode == "KEY_ENTER":

                        if container:
                            card_queue.put(container)
                            container = ""

                    else:
                        val = data.keycode.replace("KEY_", "")

                        if len(val) == 1:
                            container += val

    except:
        pass


threading.Thread(target=rfid_reader_thread, daemon=True).start()


# ================= LOCAL DATA HELPER =================

def lookup_student_local(card_id):
    """
    Searches rfid_data.txt for the card_id.

    Expected format:
    12345678,John Doe,10th
    """

    try:
        with open(get_path("rfid_data.txt"), "r") as f:

            for line in f:

                parts = line.strip().split(",")

                if len(parts) >= 3 and parts[0] == str(card_id):

                    return {
                        "id": parts[0],
                        "name": parts[1],
                        "grade": parts[2],
                    }

    except FileNotFoundError:
        print("Error: rfid_data.txt not found.")

    return None


# ================= GOOGLE SHEETS (LOGGING ONLY) =================

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    get_path("credentials.json"), scope
)

client = gspread.authorize(creds)

sheet = client.open_by_key(
    "1TALFBN-5XfLPMo898grZZkX7oTnS08Pny-yxAAjxv-4"
)

log_ws = sheet.worksheet("Log")


# ================= MAIN LOOP =================

try:

    while True:

        show_home_screen()

        fmt = "llHHi"
        size = struct.calcsize(fmt)

        try:

            with open(REMOTE_PATH, "rb", buffering=0) as f:

                in_system = True

                while in_system:

                    r, _, _ = select.select([f], [], [], 0.01)

                    cid = None

                    try:
                        cid = card_queue.get_nowait()
                    except queue.Empty:
                        pass

                    if r or cid:

                        if r:
                            flush_input(f)

                        beep(0.05)

                        scan_active = True
                        last_active_time = time.time()

                        while scan_active:

                            if time.time() - last_active_time > TIMEOUT_LIMIT:
                                scan_active = False
                                in_system = False
                                break

                            oled_msg("TAP CARD")

                            while scan_active and cid is None:

                                if time.time() - last_active_time > TIMEOUT_LIMIT:
                                    scan_active = False
                                    in_system = False
                                    break

                                rs, _, _ = select.select([f], [], [], 0.01)

                                if rs:

                                    last_active_time = time.time()

                                    sub_data = f.read(size)

                                    try:
                                        unp = struct.unpack("qqHHi", sub_data)
                                    except:
                                        unp = struct.unpack("llHHi", sub_data[:16])

                                    if unp[2] == 1 and unp[4] == 1:

                                        if unp[3] in REMOTE_KEYS_CANCEL:
                                            scan_active = False
                                            in_system = False
                                            break

                                try:
                                    cid = card_queue.get_nowait()

                                    if cid:
                                        last_active_time = time.time()

                                except queue.Empty:
                                    pass

                                time.sleep(0.01)

                            if cid and scan_active:

                                beep()

                                oled_msg("SEARCHING...")

                                student = lookup_student_local(cid)

                                if student:

                                    choice = get_remote_choice(student["name"], f)

                                    if choice == "TIMEOUT":
                                        scan_active = False
                                        in_system = False

                                    elif choice and choice != "BACK":

                                        oled_msg("WORKING...")

                                        if print_tardy(student, choice):

                                            now = datetime.now()

                                            try:

                                                log_ws.append_row(
                                                    [
                                                        str(student["id"]),
                                                        student["name"],
                                                        student["grade"],
                                                        now.strftime("%I:%M %p"),
                                                        now.strftime("%m/%d/%Y"),
                                                        choice.upper(),
                                                    ]
                                                )

                                            except:
                                                print(
                                                    "Sheet log failed (Offline), but slip printed."
                                                )

                                            oled_msg("SUCCESS!")
                                            time.sleep(1)

                                        scan_active = False
                                        in_system = False

                                    else:

                                        oled_msg("CANCELLED")
                                        time.sleep(0.5)

                                        cid = None
                                        last_active_time = time.time()

                                else:

                                    oled_msg("UNKNOWN CARD")
                                    time.sleep(1)

                                    cid = None
                                    last_active_time = time.time()

                        if not in_system:
                            break

        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(1)

except KeyboardInterrupt:
    GPIO.cleanup()
