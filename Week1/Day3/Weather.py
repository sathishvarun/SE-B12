import pyautogui
import subprocess
import time
import tempfile
import shutil
import os

# ==========================================
# SETTINGS
# ==========================================

INTERVAL = 0.5

url = "https://www.timeanddate.com/weather/india/coimbatore"

folder = "/Users/sathishvarun/Downloads/SE-B12/Week1/day4"

file_name = "Coimbatore_Weather.docx"

full_file_path = os.path.join(folder, file_name)


# ==========================================
# 1. DELETE OLD WORD FILE
# ==========================================

print("Checking old Word file...")

if os.path.exists(full_file_path):
    os.remove(full_file_path)
    print("Old file deleted.")

else:
    print("No old file found.")


# ==========================================
# 2. CREATE FRESH CHROME SESSION
# ==========================================

print("Opening fresh Chrome...")

temp_profile = tempfile.mkdtemp(prefix="chrome_clean_")

subprocess.Popen([
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "--user-data-dir=" + temp_profile,
    "--no-first-run",
    "--no-default-browser-check"
])

time.sleep(.5)


# ==========================================
# 3. OPEN NEW TAB
# ==========================================

print("Opening new tab...")

pyautogui.hotkey("command", "t")

time.sleep(INTERVAL)


# ==========================================
# 4. TYPE WEBSITE URL
# ==========================================

print("Typing website URL...")

pyautogui.hotkey("command", "l")

time.sleep(INTERVAL)

pyautogui.write(
    url,
    interval=INTERVAL
)

time.sleep(INTERVAL)

pyautogui.press("enter")


# ==========================================
# 5. WAIT FOR WEBSITE
# ==========================================

print("Loading website...")

time.sleep(.5t)


# ==========================================
# 6. SELECT ALL CONTENT
# ==========================================

print("Selecting website content...")

pyautogui.hotkey("command", "a")

time.sleep(INTERVAL)

pyautogui.hotkey("command", "c")

time.sleep(INTERVAL)

print("Content copied.")


# ==========================================
# 7. OPEN MICROSOFT WORD
# ==========================================

print("Opening Microsoft Word...")

subprocess.Popen([
    "open",
    "-a",
    "Microsoft Word"
])

time.sleep(.5)


# ==========================================
# 8. CREATE NEW WORD DOCUMENT
# ==========================================

print("Creating new Word document...")

pyautogui.hotkey("command", "n")

time.sleep(.5)


# ==========================================
# 9. PASTE CONTENT
# ==========================================

print("Pasting website content...")

pyautogui.hotkey("command", "v")

time.sleep(.5)


# ==========================================
# 10. SAVE AS
# ==========================================

print("Opening Save As...")

pyautogui.hotkey("command", "shift", "s")

time.sleep(.5)


# ==========================================
# 11. GO TO SAVE FOLDER
# ==========================================

print("Selecting folder...")

pyautogui.hotkey("command", "shift", "g")

time.sleep(1)

pyautogui.write(
    folder,
    interval=0.03
)

time.sleep(1)

pyautogui.press("enter")

time.sleep(2)


# ==========================================
# 12. ENTER FILE NAME
# ==========================================

print("Entering file name...")

pyautogui.hotkey("command", "a")

time.sleep(INTERVAL)

pyautogui.write(
    file_name,
    interval=0.03
)

time.sleep(INTERVAL)

pyautogui.press("enter")

time.sleep(6)


# ==========================================
# 13. CLOSE WORD AUTOMATICALLY
# ==========================================

print("Closing Word...")

pyautogui.hotkey("command", "w")

time.sleep(3)


# ==========================================
# 14. CLOSE CHROME
# ==========================================

print("Closing Chrome...")

pyautogui.hotkey("command", "q")

time.sleep(2)


# ==========================================
# 15. DELETE TEMPORARY CHROME PROFILE
# ==========================================

shutil.rmtree(temp_profile, ignore_errors=True)


# ==========================================
# DONE
# ==========================================

print("----------------------------------------")
print("Automation completed successfully!")
print("----------------------------------------")
print("File saved:")
print(full_file_path)