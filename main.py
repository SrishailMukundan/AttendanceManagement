import time
import serial
import RPi.GPIO as GPIO
import math
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import Image, ImageDraw, ImageFont
from escpos.printer import File
from datetime import datetime
from adafruit_fingerprint import Adafruit_Fingerprint, OK, NOFINGER, NOTFOUND
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import sys
import threading
import queue
import os
import evdev
from evdev import InputDevice, categorize, ecodes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ------------------------
# Hardware Setup
# ------------------------
serial_i2c = i2c(port=1, address=0x3C)
device = ssd1306(serial_i2c)

uart = serial.Serial("/dev/serial0", baudrate=57600, timeout=1)
finger = Adafruit_Fingerprint(uart)

BTN_BACK = 17
BTN_NEXT = 27
GPIO.setmode(GPIO.BCM)
GPIO.setup(BTN_BACK, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BTN_NEXT, GPIO.IN, pull_up_down=GPIO.PUD_UP)

try:
    font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    font_enroll = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)
except:
    font_large = ImageFont.load_default()
    font_enroll = ImageFont.load_default()

def get_path(filename):
    return os.path.join(BASE_DIR, filename)

try:
    rfid_img = Image.open(get_path("rfid.png")).convert("1").resize((50, 40))
    finger_img = Image.open(get_path("fingerprint.png")).convert("1").resize((50, 40))
except:
    rfid_img = Image.new("1", (50, 40), 0)
    finger_img = Image.new("1", (50, 40), 0)

# Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(get_path("credentials.json"), scope)
client = gspread.authorize(creds)
sheet = client.open_by_key("1TALFBN-5XfLPMo898grZZkX7oTnS08Pny-yxAAjxv-4")
rfid_ws = sheet.worksheet("RFID")
finger_ws = sheet.worksheet("Fingerprint")
log_ws = sheet.worksheet("Log")

# State
current_state = "HOME"
menu_index = -1
last_move_time = time.time()
SELECT_DELAY = 0.6 
selected_student = None
card_id = None
card_queue = queue.Queue()

# ------------------------
# RFID Thread
# ------------------------
def card_reader_thread():
    dev_path = '/dev/input/by-id/usb-413d_2107-event-kbd'
    try:
        reader = InputDevice(dev_path)
        container = ""
        for event in reader.read_loop():
            if event.type == ecodes.EV_KEY:
                data = categorize(event)
                if data.keystate == 1:
                    if data.keycode == 'KEY_ENTER':
                        if container: card_queue.put(container)
                        container = ""
                    else:
                        val = data.keycode.replace('KEY_', '')
                        if len(val) == 1: container += val
    except: pass

threading.Thread(target=card_reader_thread, daemon=True).start()

# ------------------------
# Utility Functions
# ------------------------
def log_entry(scanner_type, student_id, name, grade, status="N/A"):
    now = datetime.now()
    log_ws.append_row([
        str(student_id), scanner_type, name, grade,
        now.strftime("%I:%M %p"), now.strftime("%m/%d/%Y"), status
    ])

def print_tardy(student, absence):
    now = datetime.now()
    date_str = now.strftime("%m/%d/%Y")
    time_str = now.strftime("%I:%M").lstrip("0")
    is_am = now.strftime("%p") == "AM"
    try:
        img = Image.open(get_path("tardy_slip.png")).convert("1")
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        draw.text((100, 75), student["name"], font=font, fill=0)
        draw.text((455, 75), student["grade"], font=font, fill=0)
        draw.text((100, 135), date_str, font=font, fill=0)
        draw.text((385, 135), time_str, font=font, fill=0)
        line_y = 140 if is_am else 160
        draw.line((460, line_y, 485, line_y), fill=0, width=3)
        if absence == "excused": draw.text((25, 320), "✓", font=font, fill=0)
        else: draw.text((25, 340), "✓", font=font, fill=0)
        img_rotated = img.rotate(90, expand=True).resize((580, 800))
        p = File("/dev/usb/lp0")
        try: p.image(img_rotated); p.cut()
        finally: p.close()
    except: pass

def enroll_fingerprint():
    target_id = None
    for slot in range(1, 128):
        if finger.load_model(slot) != OK:
            target_id = slot
            break
    if not target_id: return
    while True:
        with canvas(device) as draw:
            draw.text((0, 5), f"ID: {target_id}", fill=255, font=font_enroll)
            draw.text((0, 20), "Place finger", fill=255, font=font_enroll)
            draw.text((0, 32), "for scan 1", fill=255, font=font_enroll)
        if finger.get_image() == OK and finger.image_2_tz(1) == OK: break
        if not GPIO.input(BTN_BACK): return
    while finger.get_image() != NOFINGER:
        with canvas(device) as draw: draw.text((0, 20), "Remove finger", fill=255, font=font_enroll)
        time.sleep(0.1)
    time.sleep(0.5)
    while True:
        with canvas(device) as draw:
            draw.text((0, 5), f"ID: {target_id}", fill=255, font=font_enroll)
            draw.text((0, 20), "Place SAME", fill=255, font=font_enroll)
            draw.text((0, 32), "finger again", fill=255, font=font_enroll)
        if finger.get_image() == OK and finger.image_2_tz(2) == OK: break
        if not GPIO.input(BTN_BACK): return
    if finger.create_model() == OK and finger.store_model(target_id) == OK:
        finger_ws.append_row([target_id, f"Person {target_id}"])
        with canvas(device) as draw: draw.text((20, 25), "ENROLL OK", fill=255)
    else:
        with canvas(device) as draw: draw.text((10, 25), "ENROLL FAIL", fill=255)
    time.sleep(2)

def draw_loading_bar(draw, x, y, width, height, progress):
    draw.rectangle((x, y, x + width, y + height), outline=255, fill=0)
    fill_width = int((progress / 100) * (width - 2))
    if fill_width > 0:
        draw.rectangle((x + 1, y + 1, x + fill_width, y + height - 1), outline=0, fill=255)

# ------------------------
# UI Rendering
# ------------------------
def update_display():
    global menu_index
    with canvas(device) as draw:
        if current_state == "HOME":
            draw.text((0, 2), "SPB Front Office", fill=255, font=font_large)
            draw.line((0, 20, 128, 20), fill=255)
            s_f, s_t = (255, 0) if menu_index == 0 else (0, 255)
            draw.rectangle((8, 28, 60, 48), outline=255, fill=s_f); draw.text((20, 33), "SETUP", fill=s_t)
            sc_f, sc_t = (255, 0) if menu_index == 1 else (0, 255)
            draw.rectangle((68, 28, 120, 48), outline=255, fill=sc_f); draw.text((80, 33), "SCAN", fill=sc_t)
        
        elif current_state in ["SETUP_MENU", "SCAN_MENU"]:
            label = "SETUP:" if current_state == "SETUP_MENU" else "SCAN:"
            draw.text((10, 2), label, fill=255)
            l_f, l_i = (255, 0) if menu_index == 0 else (0, 255)
            draw.rectangle((8, 18, 62, 62), outline=255, fill=l_f); draw.bitmap((10, 20), rfid_img, fill=l_i)
            r_f, r_i = (255, 0) if menu_index == 1 else (0, 255)
            draw.rectangle((66, 18, 120, 62), outline=255, fill=r_f); draw.bitmap((68, 20), finger_img, fill=r_i)

        elif current_state == "FINGER_SETUP":
            draw.text((10, 2), "FINGERPRINT SETUP", fill=255)
            n_f, n_t = (255, 0) if menu_index == 0 else (0, 255)
            draw.rectangle((10, 20, 118, 38), outline=255, fill=n_f); draw.text((30, 25), "ENROLL NEW", fill=n_t)
            c_f, c_t = (255, 0) if menu_index == 1 else (0, 255)
            draw.rectangle((10, 42, 118, 60), outline=255, fill=c_f); draw.text((30, 47), "CLEAR ALL", fill=c_t)

        elif current_state == "CONFIRM_CLEAR":
            draw.text((10, 2), "CLEAR ALL?", fill=255)
            can_f, can_t = (255, 0) if menu_index == 0 else (0, 255)
            draw.rectangle((10, 20, 118, 38), outline=255, fill=can_f); draw.text((40, 25), "CANCEL", fill=can_t)
            ok_f, ok_t = (255, 0) if menu_index == 1 else (0, 255)
            draw.rectangle((10, 42, 118, 60), outline=255, fill=ok_f); draw.text((55, 47), "OK", fill=ok_t)

        elif current_state == "ABSENCE_MENU":
            draw.text((10, 2), "Status?", fill=255)
            options = ["EXCUSED", "UNEXCUSED", "NEITHER"]
            start_idx = 0 if menu_index <= 0 else 1
            for i in range(2):
                opt_idx = start_idx + i
                y_pos = 18 + (i * 22)
                is_selected = (menu_index == opt_idx)
                bg_col, txt_col = (255, 0) if is_selected else (0, 255)
                draw.rectangle((10, y_pos, 118, y_pos + 18), outline=255, fill=bg_col)
                draw.text((25, y_pos + 2), options[opt_idx], fill=txt_col, font=font_enroll)

        elif current_state in ["RFID_WAIT", "RFID_WAIT_SETUP", "FINGER_WAIT"]:
            msg = "SCAN FINGER" if current_state == "FINGER_WAIT" else "TAP CARD"
            draw.text((15, 15), msg, fill=255, font=font_large)
            bv = (math.sin(time.time() * 8) + 1) * 50
            draw_loading_bar(draw, 14, 40, 100, 8, bv)
# ------------------------
# Main Loop
# ------------------------
update_display()
try:
    while True:
        now = time.time()
        # Back Button
        if not GPIO.input(BTN_BACK):
            current_state = "HOME"; menu_index = -1; card_id = None; update_display()
            time.sleep(0.3); continue

        # Next Button / Auto-Select
        if not GPIO.input(BTN_NEXT):
            if current_state in ["HOME", "SETUP_MENU", "SCAN_MENU", "FINGER_SETUP", "CONFIRM_CLEAR", "ABSENCE_MENU"]:    
                max_opts = 3 if current_state == "ABSENCE_MENU" else 2
                menu_index = 0 if menu_index == -1 else (menu_index + 1) % max_opts
                last_move_time = now; update_display(); time.sleep(0.2)

        if menu_index != -1 and (now - last_move_time) > SELECT_DELAY:
            if current_state == "HOME":
                current_state = "SETUP_MENU" if menu_index == 0 else "SCAN_MENU"
            elif current_state == "SETUP_MENU":
                current_state = "RFID_WAIT_SETUP" if menu_index == 0 else "FINGER_SETUP"
            elif current_state == "SCAN_MENU":
                current_state = "RFID_WAIT" if menu_index == 0 else "FINGER_WAIT"
            elif current_state == "FINGER_SETUP":
                if menu_index == 0: enroll_fingerprint()
                else: current_state = "CONFIRM_CLEAR"
            elif current_state == "CONFIRM_CLEAR":
                if menu_index == 1:
                    finger.empty_library(); finger_ws.delete_rows(2, 500)
                    with canvas(device) as draw: draw.text((10, 25), "CLEARED", fill=255)
                    time.sleep(1.5)
                current_state = "HOME"
            elif current_state == "ABSENCE_MENU":
                status = "N/A"
                if menu_index == 0: print_tardy(selected_student, "excused"); status = "Excused"
                elif menu_index == 1: print_tardy(selected_student, "unexcused"); status = "Unexcused"
                elif menu_index == 2: status = "Neither"
                log_entry("RFID", card_id, selected_student["name"], selected_student["grade"], status)
                current_state = "RFID_WAIT" # Go back to scanning mode
            menu_index = -1; update_display()

        # RFID Logic (Wait States)
        if current_state in ["RFID_WAIT", "RFID_WAIT_SETUP"]:
            update_display() # This makes the loading bar move for RFID
            try:
                cid = card_queue.get_nowait()
                if current_state == "RFID_WAIT_SETUP":
                    rfid_ws.append_row([str(cid)])
                    with canvas(device) as draw: draw.text((10, 25), "STORED", fill=255)
                    time.sleep(1.5); current_state = "SETUP_MENU"
                else:
                    all_ids = rfid_ws.col_values(1)
                    if str(cid) in all_ids:
                        idx = all_ids.index(str(cid)) + 1
                        card_id = cid
                        selected_student = {"name": rfid_ws.cell(idx, 2).value, "grade": rfid_ws.cell(idx, 3).value}
                        current_state = "ABSENCE_MENU"; menu_index = -1
                    else:
                        with canvas(device) as draw: draw.text((10, 25), "UNKNOWN", fill=255)
                        time.sleep(1.5); current_state = "RFID_WAIT"
                update_display()
            except queue.Empty: pass

        # Fingerprint Logic (Wait State)
        if current_state == "FINGER_WAIT":
            update_display() # Keep loading bar moving
            if finger.get_image() == OK and finger.image_2_tz(1) == OK:
                if finger.finger_search() == OK:
                    all_f = finger_ws.col_values(1); fid_s = str(finger.finger_id)
                    if fid_s in all_f:
                        name = finger_ws.cell(all_f.index(fid_s) + 1, 2).value
                        log_entry("Fingerprint", fid_s, name, "N/A", "N/A")
                        with canvas(device) as draw:
                            draw.text((20, 20), "Hello", fill=255, font=font_large)
                            draw.text((20, 40), name, fill=255, font=font_large)
                        time.sleep(2); current_state = "FINGER_WAIT"
                    else:
                        with canvas(device) as draw: draw.text((10, 25), "UNKNOWN", fill=255)
                        time.sleep(1.5); current_state = "FINGER_WAIT"
                else:
                    with canvas(device) as draw: draw.text((10, 25), "UNKNOWN", fill=255)
                    time.sleep(1.5); current_state = "FINGER_WAIT"
            update_display()

        time.sleep(0.05)
except KeyboardInterrupt:
    GPIO.cleanup()
