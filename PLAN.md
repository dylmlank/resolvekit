# ResolveKit Media Provider Implementation Plan

## Overview
Implement a real media provider to replace the StubProvider placeholder. ResolveKit already uses native Anthropic SDK; the gap is media-generation capability (clips, overlays, captions, transitions).

## Current State
- **SDK:** Native `anthropic` SDK (core/claude.py:13-18, model="claude-opus-4-8")
- **Tool base:** 18 tools in `core/tools.py` (~19KB)
- **DaVinci bridge:** `core/bridge.py:33-51` → DaVinciResolveScript fusionscript.dll
- **UI:** Electron panel (manifest.xml, main.js, renderer.js) + WebSocket backend (server.py:44)
- **Media gap:** `core/providers.py:33-80`, StubProvider at :40 is a placeholder; MediaProvider protocol exists

## Phase 1: Provider Design
1. Review `core/providers.py` MediaProvider protocol spec
   - [ ] List required methods: generate_clip? generate_overlay? add_captions?
   - [ ] Define input/output contract (timeline position, duration, text, etc.)
2. Decide provider strategy
   - **Option A (simple):** Stub → ffmpeg-based local video composition (caption burns, fade overlays, basic transitions)
   - **Option B (featured):** Stub → external service (Replicate, RunwayML, or local Stable Diffusion for generative media)
   - **Option C (hybrid):** Both, with user config switch

## Phase 2: StubProvider → RealProvider
1. Replace StubProvider with implementation matching chosen strategy
2. Implement each MediaProvider method with DaVinci API calls (core/bridge.py already bridges DaVinciResolveScript)
3. Test integration
   - [ ] Generate a clip (e.g., add 2s fade overlay on timeline)
   - [ ] Add captions to a clip
   - [ ] Apply transition effect

## Phase 3: Electron Panel UX
1. Add media-gen tools to panel sidebar or a dedicated "Media" tab
2. Connect UI controls to agent tool invocations
3. Stream back preview or confirmation (already WebSocket-connected)

## Phase 4: Testing
- [ ] End-to-end: user creates project → agent gen captions → captions appear on timeline
- [ ] Verify DaVinci API call chain (bridge → fusionscript.dll → timeline update)
- [ ] Test with real Resolve project (5+ clips minimum)

## Success Criteria
- StubProvider replaced with real implementation ✓
- At least one media-gen capability (captions OR overlays OR clips) working ✓
- Electron panel + WebSocket + agent loop handles user requests ✓
- DaVinci timeline reflects generated media ✓

## Notes
- fusionscript.dll path may need discovery on Windows; document in README
- ffmpeg (option A) requires Windows binary or conda env setup
- RunwayML/Replicate (option B) require API keys; add to .env example
