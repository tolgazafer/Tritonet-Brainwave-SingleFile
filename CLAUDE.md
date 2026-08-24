# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run locally** (required — `file://` is blocked by browser MIDI/audio permissions):
```bash
cd "JavaScript"
python3 -m http.server 8080
# Open http://localhost:8080
```

**Build the self-contained single-file artifact:**
```bash
python3 build_single_file.py
# Outputs: Tritonet_Brainwave_SingleFile.html (and Tritonet-Web-Embed-Repo/dist/Tritonet_Web.html)
```

The build script fetches p5.js v1.9.0 from CDN (cached in `.cache/`), concatenates the JS modules in the required load order, and inlines everything into one HTML file.

No test runner, linter, or package.json exists. This is plain JS with no build toolchain beyond the Python script.

## Architecture

### Entry point and module load order

`JavaScript/index.html` is the entry point. It loads modules via `<script>` tags in this strict order (the build script enforces the same order):

```
config → colors → themes → mpe → sequencer → state → audio-midi → core → drawing → gui-input
```

Order matters: every module uses bare globals from earlier modules. There is no module system (`import`/`require`) — all state and functions are globals on `window`.

> **`JavaScript/Tritonet_Brainwave.js` is a legacy monolith and NOT the active entry point.** The `js/` modules are the working codebase.

### Global state

All application state lives as bare globals, primarily declared in `js/state.js`. Key state:

| Variable | Role |
|---|---|
| `anchor` (0–6) | Root position on Circle of Fifths — the primary musical input |
| `center`, `centermove` | Table (key signature) position |
| `chooser` (0–6) | Chord voicing/inversion selector |
| `modecenter` (0–6) | Modal center (Lydian=0 → Locrian=6) |
| `nl` | Nightline — chromatic shift applied to the circle |
| `chord[3]` | Current chord intervals |
| `channelVariables[16]` | Per-MIDI-channel parameters (PerChannelParameters objects: velocity, voices, SATB ranges, result notes) |
| `currentLook` | Active visual theme |
| `seqPattern[16]`, `seqRunning` | Sequencer step data and playback state |
| `mpeEnabled`, `currentTuning` | MPE and microtonal tuning state |

### The calculator chain (core music engine)

Every chord change flows through this pipeline in `js/core.js`:

```
TableCalculator()
  → ModeCalculator()        — adjusts nightline (nl) so modal center matches
    → ChooserCalculator()   — highlights selected voicing
      → AnchorCalculator()  — computes tint color and voice assignments
        → TritonetLaZaku()  — master compute: calls voiceleading() for all 16 channels
          → voiceleading()  — per-channel: 4-voice SATB note assignment with voice-leading rules
            → PlaybackOn()  — sends MIDI Note On (and MidiCC() for CC output)
```

`notahesap()` (also in `core.js`) is the top-level trigger: it kills all active notes, then calls the full chain. Call this whenever you need to retrigger the current chord.

### Module responsibilities

| File | Owns |
|---|---|
| `js/config.js` | MIDI CC number assignments (documentation comments) |
| `js/colors.js` | Color palette tokens (DefaultColor1–7, HighlightColor, etc.) |
| `js/themes.js` | `VIEW_THEMES` map, `setLook()`, globe/star state |
| `js/mpe.js` | MPE channel pool, microtonal tuning systems (12-TET, Just, Arabic, Turkish, Indian Shruti) |
| `js/sequencer.js` | 16-step sequencer: tempo, swing, step direction, `seqPattern[]` |
| `js/state.js` | All global state variables + `SampleWidget`, `PerChannelParameters`, `StorageTable` classes + tween system |
| `js/audio-midi.js` | Web MIDI API init/I/O, internal Web Audio fallback synth, `sendNoteOn/Off/Controller()`, `panicAllNotesOff()` |
| `js/core.js` | Calculator chain, `voiceleading()`, `notahesap()`, `PlaybackOn/Off()`, `MidiCC()` |
| `js/drawing.js` | p5.js `setup()`/`draw()` loop, all canvas rendering (circle, zodiac, calculator, notation views) |
| `js/gui-input.js` | `setupGUI()`, keyboard/mouse handlers, MIDI dropdown wiring, `updateGUIFromState()` |

### MIDI output

MIDI is sent from `js/audio-midi.js` using raw Web MIDI status bytes:
- Note On: `[0x90 + ch, note, vel]`
- Note Off: `[0x80 + ch, note, 0]`
- CC: `[0xB0 + ch, cc, val]`

When no MIDI device is selected, the app falls back to an internal sine-wave synth via Web Audio API. CC20–23 = SATB transpose; CC30–33 = SATB resonance; CC40 = anchor; CC60 = mode; CC61 = root.

### Lesson / AI Teacher system

`JavaScript/lesson_runner.html` embeds `index.html` in an iframe and communicates via `postMessage`:
- Runner → app: `{ target: 'tritonet-api', command, payload, id }`
- App → runner: `{ target: 'tritonet-api-response', id, ok, result }`

Lesson content is JSON files in `teacher/` (catalog: `index.json`; lessons: `lesson_XX_name.json`). Each lesson has steps with optional `tritonet` state configs. The teacher panel uses the Claude API for free-form Q&A — key is `TRITONET_CLAUDE_API_KEY` (runtime variable, never stored in lesson files).

### Embed repo

`Tritonet-Web-Embed-Repo/` is a standalone sub-repository for iframe embedding. Its `dist/Tritonet_Web.html` is updated by copying the build output:
```bash
cp Tritonet_Brainwave_SingleFile.html Tritonet-Web-Embed-Repo/dist/Tritonet_Web.html
```
