# Attendance Managemetn System

A Raspberry Pi-based attendance terminal featuring RFID and Fingerprint scanning, Google Sheets integration, and thermal receipt printing.

## Hardware Setup
- **OLED:** SSD1306 (I2C)
- **Fingerprint:** Adafruit Optical (UART /dev/serial0)
- **Printer:** USB Thermal Printer (/dev/usb/lp0)
- **Buttons:** GPIO 17 (Back), GPIO 27 (Next)

## Software Installation
1. Enable I2C and Serial via `sudo raspi-config`.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
