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
## 🔑 Google Sheets API Setup

This project uses Google Sheets to log attendance. To set this up, you need a `credentials.json` file in the root directory.

### 1. Create Google Cloud Project
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a **New Project** named `Attendance-System`.

### 2. Enable APIs
Search for and **Enable** the following two APIs:
* **Google Sheets API**
* **Google Drive API**

### 3. Create Credentials
1. Go to **APIs & Services > OAuth consent screen**. 
   * Select **External**, fill in the app name and your email, then save.
2. Go to **APIs & Services > Credentials**.
3. Click **+ Create Credentials** > **OAuth client ID**.
4. Select **Desktop app** as the application type.
5. Download the JSON file and rename it to `credentials.json`.

### 4. Local Setup
1. Place the `credentials.json` file in the main folder of this repository.
2. The first time you run `Attendance.py`, a browser window will open asking for permission. 
3. After authorizing, a `token.json` file will be created automatically to handle future logins.

> **⚠️ Security Note:** Do NOT upload `credentials.json` or `token.json` to GitHub.
