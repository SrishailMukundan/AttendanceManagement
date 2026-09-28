# Attendance Management System

A Raspberry Pi 4B-powered attendance terminal featuring 125kHz RFID card scanning, dual OLED status displays, Google Sheets cloud logging, wireless remote menu navigation, and automated thermal tardy slip printing.
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23005120.svg)](https://doi.org/10.5281/zenodo.23005120)

---

## 🛠️ System Architecture & Features

- **RFID Attendance Scanning:** Quick scan using 125kHz RFID cards with audio confirmation.
- **Interactive Menu:** Office staff can categorize attendance on screen using a wireless presentation remote:
  - **Excused** (Prints tardy slip & logs to spreadsheet)
  - **Unexcused** (Prints tardy slip & logs to spreadsheet)
  - **Neither** (Campus check-in/check-out; logs to spreadsheet without printing)
- **Thermal Slip Generation:** Automatically prints physical 80mm tardy passes with student details, grade, timestamp, and tardy type.
- **Cloud Integration:** Real-time logging of student ID, name, grade, date, time, and status to Google Sheets.
- **Custom Enclosure:** Includes CAD models for 3D printing a custom tabletop chassis.

---

## Hardware Setup
| Component | Specification |
| :--- | :--- |
| **SBC** | Raspberry Pi 4B |
| **RFID Reader** | 125kHz USB RFID Reader |
| **Primary Display** | 2.42" OLED |
| **Status Display** | 0.96" OLED (I2C / SSD1306) |
| **Printer** | 80mm USB Thermal Receipt Printer (`/dev/usb/lp0`) |
| **Navigation** | USB Wireless Presentation Remote / Clicker |
| **Enclosure** | Custom 3D Printed Chassis (STEP/CAD files in `/3dPrintFiles`) |


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
