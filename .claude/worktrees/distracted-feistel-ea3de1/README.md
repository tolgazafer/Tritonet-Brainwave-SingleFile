# Tritonet Brainwave (Single File)

Standalone browser build of Tritonet Brainwave.

## Screenshot

![Tritonet Brainwave UI](docs/screenshot.png)

Place your screenshot image at `docs/screenshot.png` to render it here on GitHub.

## Run locally

Use a local HTTP server (recommended for browser permissions and stable asset behavior):

```bash
cd /path/to/Tritonet\ JavaScript
python3 -m http.server 8080
```

Then open:

- http://localhost:8080/Tritonet_Brainwave_SingleFile.html

## Rebuild the single file

If you update source code and want to re-inline dependencies into one artifact:

```bash
cd /path/to/Tritonet\ JavaScript
python3 build_single_file.py
```

This updates `Tritonet_Brainwave_SingleFile.html` and inlines `p5.js` so the app no longer depends on a CDN script tag.

## Browser notes

- Use Chrome or Safari.
- Web MIDI and audio features can require user interaction and browser permission prompts.
- Opening via `file://` is not recommended.

## Repository contents

- `Tritonet_Brainwave_SingleFile.html`: self-contained application build.
- `build_single_file.py`: inlines `p5.js` into the single-file build artifact.
- `.gitignore`: excludes local environment and source folders from this single-file repo.
