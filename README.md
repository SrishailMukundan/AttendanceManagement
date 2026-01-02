# AttendanceManagement


This code acts as a complete Front Office Attendance and Enrollment Terminal. It handles student identification through two different biometric/hardware methods and integrates with a cloud database and a physical printer.
Here are the specific functionalities supported:
1. Dual-Method Student Scanning
RFID Scanning: Supports USB RFID card readers. When a card is tapped, the system looks up the student in the Google Sheet.
Fingerprint Scanning: Uses an optical or capacitive sensor to identify students by their finger ID. Unlike RFID, this is a "Direct Login"—it identifies the person and logs them immediately without extra menus.
2. Automated Logging (Google Sheets)
Cloud Syncing: Every successful scan (RFID or Fingerprint) is timestamped and uploaded to a "Log" worksheet.
Data Points: It records the Student ID, the type of scanner used (RFID vs. Fingerprint), Name, Grade, Time, and Date.
3. Tardy Slip Printing (RFID Only)
Status Selection: For RFID scans, the code triggers a "Status" menu: Excused, Unexcused, or Neither.
Physical Output: If "Excused" or "Unexcused" is selected, it generates a graphical tardy slip using a template (tardy_slip.png), overlays the student's data, rotates it for the printer, and prints it via a USB thermal printer.
Smart Formatting: It automatically calculates AM/PM and strikes through the correct period on the slip.
4. Administrative Setup & Enrollment
RFID Enrollment: Allows you to "Register" new cards. When a new card is tapped in Setup mode, its UID is saved to the database.
Fingerprint Enrollment: A step-by-step process that:
Finds the next empty slot on the sensor.
Prompts for two scans of the same finger to ensure a high-quality template.
Stores the ID in the Google Sheet.
Database Management: Includes a "Clear All" function to wipe the fingerprint sensor's internal memory and the corresponding sheet rows simultaneously.
5. UI and Safety Features
Confirmation Prompts: To prevent accidental data loss, the "Clear All" function requires an explicit "OK" confirmation.
Navigation Logic: Uses a "Hold-to-Select" timer system. You click the button to move the highlight box and let it sit for 0.6 seconds to "Enter" a menu.
Dynamic Visuals: Includes a pulsing loading bar on "Wait" screens to let the user know the system hasn't frozen.
Back Navigation: A dedicated hardware button (GPIO 17) allows the user to exit any sub-menu and return to the Home screen instantly.
