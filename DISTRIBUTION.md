# Distributing Student Command Centre

## What buyers need to know (put this on your itch.io page)

1. Download and run `StudentCommandCentre.exe` — no installation needed.
2. On first launch, the Study Buddy / Planner features ask for a **free Groq
   API key**: get one at https://console.groq.com/keys (takes a minute).
3. Create a plain text file named `.env` **next to the exe** containing:
   ```
   GROQ_API_KEY=gsk_your_key_here
   ```
4. Windows SmartScreen may warn about unsigned apps — choose "More info" →
   "Run anyway".

Everything else (tasks, exams, subjects, progress, notifications) works
without any key. Data is stored in a `data` folder next to the exe — delete
it to reset the app.

## IMPORTANT - before you upload

- NEVER copy your own `.env` or paste your own `GROQ_API_KEY` into the dist
  folder. Anyone who downloads the zip could extract and steal your key
  (and it has billing attached to your Groq account).
- The exe is unsigned. To reduce SmartScreen warnings you can code-sign it
  later (optional, costs money).
- Rebuild after code changes:
  ```
  python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name StudentCommandCentre --icon assets\app_icon.ico ^
    --add-data "assets\app_icon.png;assets" ^
    --add-data "assets\logo_lockup.png;assets" main.py
  ```

## Suggested itch.io page text

**Student Command Centre** — your study hub with an AI tutor.

Track exams, tasks and subjects, build AI study plans, earn XP and streaks,
and get smart reminders before every exam. Includes Study Buddy, a friendly
AI tutor powered by GPT-OSS (bring your own free Groq API key — instructions
included).

- 🪟 Windows 10/11, portable, no installation
- 🤖 AI tutor + AI study planner
- 🔔 Smart reminders and reward system
