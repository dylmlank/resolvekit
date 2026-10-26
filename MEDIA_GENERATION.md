# ResolveKit Media Generation

ResolveKit can generate media files (images and audio) and import them directly into your DaVinci Resolve timeline. This enables Claude to create visual and audio assets end-to-end.

## Providers

ResolveKit ships with two media providers:

### `LocalProvider` (default)
Uses PIL (Pillow) + NumPy for local, fast generation:
- **Images:** Gradient backgrounds (mood-matched colors) with text overlay
- **Audio:** Tone-based WAV files (mood-matched frequency)
- **Stock:** Placeholder (can be upgraded to Pexels/Pixabay API)

**Requirements:** `pillow>=10.0`, `numpy>=1.24`

**Setup:** Install dependencies (already in `requirements.txt`):
```bash
pip install pillow numpy
```

**Usage:** Already default. Verify in `.env`:
```env
RESOLVEKIT_PROVIDER=local
```

### `StubProvider` (fallback)
Writes placeholder files if PIL/NumPy aren't available:
- **Images:** Colored placeholder cards with text
- **Audio:** Silent WAV files (duration matched to prompt)
- **Stock:** Text message (no actual files)

**No dependencies required.** Used if `LocalProvider` fails or `RESOLVEKIT_PROVIDER=stub` in `.env`.

## Tools

Available to Claude in your Resolve session:

### `generate_image_clip`
Generate an image and optionally append it to the timeline.
```
Prompt: "a sunset gradient with 'END CREDITS' text"
Mood: "warm" | "calm" | "epic" | ... (affects color)
add_to_timeline: true/false
```
Returns: Path to generated PNG + "appended to timeline" if requested.

### `generate_music_clip`
Generate an audio track (currently tone-based) and optionally append it.
```
Prompt: "ambient background track"
Seconds: 5-60 (duration)
Mood: "calm" | "energetic" | ... (affects frequency/tone)
add_to_timeline: true/false
```
Returns: Path to generated WAV + "appended to timeline" if requested.

### `find_stock`
Placeholder for stock footage search (not yet live).
```
Query: "sunset over water"
Kind: "video" | "image" | "music"
```
Returns: Currently a message describing what would be searched.

### `import_media`
Import any media file(s) into Resolve's media pool.
```
Paths: ["C:\\path\\to\\video.mp4", "C:\\path\\to\\image.png", ...]
```
Returns: List of imported media names.

## Workflow Example

**Prompt to Claude:**
> "Create a 10-second intro sequence. Generate a gradient image with 'PROJECT' text, then generate 5 seconds of calm ambient audio, and put both on the timeline."

**Claude's steps:**
1. Calls `generate_image_clip` → `img_project.png` (gradient, warm colors)
2. Calls `generate_music_clip` → `music_ambient.wav` (5s, calm tone)
3. Both appended to timeline automatically
4. You now have a ready-to-use intro on your timeline

## Extending the Providers

To add a real image or music API:

1. **Create a new provider class** in `core/providers.py`:
```python
class ReplicateProvider:
    name = "replicate"
    
    def generate_image(self, prompt, mood="neutral"):
        # Call Replicate API (e.g., SDXL)
        # Return path to saved image
        ...
    
    def generate_music(self, prompt, seconds=10, mood="neutral"):
        # Call music API (e.g., Jukebox, Riffusion)
        # Return path to saved WAV
        ...
```

2. **Update `get_provider()`** to instantiate it:
```python
def get_provider():
    choice = os.environ.get("RESOLVEKIT_PROVIDER", "local")
    if choice == "replicate":
        return ReplicateProvider()
    ...
```

3. **Add API key to `.env`**:
```env
RESOLVEKIT_PROVIDER=replicate
REPLICATE_API_KEY=r8_...
```

4. **Update `requirements.txt`** with any new dependencies.

## Troubleshooting

**"PIL not installed"**
```bash
pip install pillow
```

**"numpy not installed"**
```bash
pip install numpy
```

**"Error: provider not found"**
- Check `.env` has valid `RESOLVEKIT_PROVIDER` value (local|stub)
- If misspelled, defaults to StubProvider (no error, just placeholder files)

**Generated media won't import**
- Verify `RESOLVEKIT_OUTPUT` folder exists and is writable
- Check that DaVinci Resolve is running
- Ensure media pool is visible in Resolve

**Audio sounds wrong / is silent**
- LocalProvider generates tones; if you want silence, use StubProvider
- For custom audio, upgrade to a real music API (Replicate, ElevenLabs, etc.)

## Next Steps

- [ ] Pexels/Pixabay API for `find_stock`
- [ ] Replicate SDXL integration for `generate_image`
- [ ] Jukebox or similar for `generate_music`
- [ ] FFmpeg-based transitions and compositing
