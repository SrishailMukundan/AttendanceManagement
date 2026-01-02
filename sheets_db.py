import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

class SheetsDB:
    def __init__(self, json_path, sheet_key):
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(json_path, scope)
        client = gspread.authorize(creds)
        self.sheet = client.open_by_key(sheet_key)
        self.rfid_ws = self.sheet.worksheet("RFID")
        self.finger_ws = self.sheet.worksheet("Fingerprint")
        self.log_ws = self.sheet.worksheet("Log")

    def log_entry(self, scanner_type, student_id, name, grade):
        now = datetime.now()
        self.log_ws.append_row([
            student_id, scanner_type, name, grade, 
            now.strftime("%I:%M %p"), now.strftime("%m/%d/%Y")
        ])

    def get_student_by_rfid(self, card_id):
        all_ids = self.rfid_ws.col_values(1)
        if card_id in all_ids:
            idx = all_ids.index(card_id) + 1
            return {"name": self.rfid_ws.cell(idx, 2).value, "grade": self.rfid_ws.cell(idx, 3).value}
        return None
