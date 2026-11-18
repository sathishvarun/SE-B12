# "How to use Virundhu" video (silent, full HD)

Builds `frontend/public/demo/howto.mp4` (1920x1080, 30 fps, no audio) and `howto.json` (when each step starts, used
for the step list next to the player). Each step shows a caption card "STEP n OF 14", a title and one line of how-to;
an orange marker shows where to click. The opening and closing cards show the founder's photo
(`frontend/public/demo/presenter.jpg`).

Needs: the app running on ports 8450/5450, Xvfb, ffmpeg, Playwright with Chromium.

1. `python seed_demo_restaurant.py` – makes the fictional "Annapoorna Mess" and prints its owner email.
2. Copy that outlet's feedback link (Settings → Outlets → QR code link, e.g. http://localhost:5450/f/xxxx?o=12).
3. `python rec.py <owner email> <feedback link>` – records to /tmp/howto/screen.mp4 and timeline.json.
4. `ffmpeg -i /tmp/howto/screen.mp4 -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -movflags +faststart -an howto.mp4`
5. Copy `howto.mp4` and `timeline.json` (as `howto.json`) to `frontend/public/demo/`.

To change the steps or wording, edit the `@step("Title", "Explanation")` blocks in `rec.py`.
Don't edit website files while it records: the page reloads and the recording shows a blank screen.
