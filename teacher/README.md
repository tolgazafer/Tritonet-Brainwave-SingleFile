# Tritonet Teacher

This folder contains the lesson content for the AI Teacher panel.

## Structure

- `index.json` — lesson registry (list of all available lessons)
- `lesson_XX_name.json` — individual lesson files

## Lesson format

Each lesson JSON file contains:
- `id` — unique lesson identifier
- `title` — display title
- `level` — beginner / intermediate / advanced
- `topics` — array of topic tags (e.g. "intervals", "voice-leading", "modes")
- `intro` — introductory text shown when the lesson loads
- `steps` — array of step objects:
  - `text` — instruction or explanation
  - `hint` — optional hint shown on demand
  - `tritonet` — optional Tritonet state to set (key, mode, anchor, voices)
  - `listen` — if true, wait for user to perform the step before continuing

## How lessons connect to Tritonet

The teacher panel (when implemented in `teacher.js`) will:
1. Load `teacher/index.json` to populate the lesson list
2. Load a chosen lesson file and walk through steps
3. Optionally call `setLook()`, `nota1`, `anchor`, etc. to configure the Tritonet
   canvas to match the lesson context
4. Use the Claude API (via fetch) to answer free-form questions in the chat input

## Claude API key

Set `TRITONET_CLAUDE_API_KEY` as a runtime variable or enter it in the teacher
panel UI. The key is never stored in lesson files.
