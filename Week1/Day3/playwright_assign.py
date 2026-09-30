import asyncio
import pandas as pd
import os
from datetime import datetime

from playwright.async_api import async_playwright


# ==========================================
# SETTINGS
# ==========================================

EXCEL_FILE = "contacts.xlsx"

SCREENSHOT_FOLDER = "screenshots"

REPORT_FILE = "whatsapp_report.xlsx"

WAIT_TIME = 0.5


# ==========================================
# 0.5 SECOND WAIT
# ==========================================

async def short_wait():
    await asyncio.sleep(WAIT_TIME)


# ==========================================
# MAIN
# ==========================================

async def main():

    # --------------------------------------
    # Read Excel
    # --------------------------------------

    df = pd.read_excel(
        EXCEL_FILE,
        dtype=str
    ).fillna("")

    print("================================")
    print("Contacts loaded:", len(df))
    print("================================")


    # --------------------------------------
    # Create screenshot folder
    # --------------------------------------

    os.makedirs(
        SCREENSHOT_FOLDER,
        exist_ok=True
    )


    # --------------------------------------
    # Start Playwright
    # --------------------------------------

    async with async_playwright() as p:

        browser = await p.chromium.launch_persistent_context(
            "whatsapp_profile",
            headless=False
        )

        page = browser.pages[0]


        # ----------------------------------
        # Open WhatsApp
        # ----------------------------------

        print("Opening WhatsApp Web...")

        await page.goto(
            "https://web.whatsapp.com"
        )

        await short_wait()


        print()
        print("================================")
        print("FIRST TIME ONLY")
        print("Scan the WhatsApp QR code.")
        print("================================")
        print()


        # ==================================
        # PROCESS CONTACTS
        # ==================================

        report = []


        for index, row in df.iterrows():

            name = row["Name"].strip()

            phone = row["Phone"].strip()

            template = row["Message"].strip()


            print()
            print("--------------------------------")
            print(
                f"Processing {index + 1}/{len(df)}"
            )
            print(
                f"Name  : {name}"
            )
            print(
                f"Phone : {phone}"
            )
            print("--------------------------------")


            # --------------------------------
            # Remove +
            # --------------------------------

            phone = phone.replace("+", "")

            await short_wait()


            # --------------------------------
            # Personalize message
            # --------------------------------

            message = template.replace(
                "{name}",
                name
            )

            await short_wait()


            status = "Failed"

            screenshot = ""

            error_message = ""


            try:

                # ----------------------------
                # Open WhatsApp chat
                # ----------------------------

                url = (
                    "https://web.whatsapp.com/send"
                    "?phone="
                    + phone
                )


                print("Opening chat...")


                await page.goto(
                    url,
                    wait_until="domcontentloaded"
                )

                await short_wait()


                # ----------------------------
                # Find message box
                # ----------------------------

                print(
                    "Looking for message box..."
                )


                message_box = page.locator(
                    'footer div[contenteditable="true"]'
                ).first


                await message_box.wait_for(
                    state="visible",
                    timeout=10000
                )

                await short_wait()


                print(
                    "Message box found."
                )


                # ----------------------------
                # Type message
                # ----------------------------

                await message_box.click()

                await short_wait()


                await message_box.fill(
                    message
                )

                await short_wait()


                # ----------------------------
                # Send message
                # ----------------------------

                await page.keyboard.press(
                    "Enter"
                )

                await short_wait()


                print(
                    "Message sent successfully!"
                )


                status = "Sent"


                # ----------------------------
                # Screenshot
                # ----------------------------

                filename = (
                    f"{index + 1}_{name}.png"
                )


                filename = filename.replace(
                    "/",
                    "_"
                )

                filename = filename.replace(
                    "\\",
                    "_"
                )


                screenshot = os.path.join(
                    SCREENSHOT_FOLDER,
                    filename
                )


                await page.screenshot(
                    path=screenshot
                )

                await short_wait()


                print(
                    "Screenshot:",
                    screenshot
                )


            except Exception as e:

                error_message = str(e)

                print(
                    "ERROR:",
                    error_message
                )


            # --------------------------------
            # Save result
            # --------------------------------

            report.append({

                "Name": name,

                "Phone": row["Phone"],

                "Message": message,

                "Status": status,

                "Screenshot": screenshot,

                "Error": error_message,

                "Time": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

            })


            # --------------------------------
            # 0.5 SECOND BEFORE NEXT CONTACT
            # --------------------------------

            await short_wait()


        # ==================================
        # SAVE REPORT
        # ==================================

        report_df = pd.DataFrame(
            report
        )


        report_df.to_excel(
            REPORT_FILE,
            index=False
        )


        print()
        print("================================")
        print("AUTOMATION COMPLETED")
        print("================================")

        print(
            "Report:",
            REPORT_FILE
        )


        await browser.close()


# ==========================================
# RUN
# ==========================================

asyncio.run(main())