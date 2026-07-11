# Ditto Cinematic Motion Rebuild — Design

## Objective

Replace the first 20-second Ditto trailer with a genuinely animated cinematic film. Preserve the Roman engraving identity, the human/AI mirror concept, the no-voiceover format, and the final message, while eliminating the stop-start edit and the feeling of camera moves over still pictures.

## Diagnosed failure

The delivered MP4 is technically healthy: 20 seconds, 60 fps, and 1,200 evenly timed frames. The perceived lag comes from the edit architecture, not the encoder.

- Fifteen shots create fourteen boundaries in twenty seconds.
- Most shots restart a new eased camera transform, producing repeated acceleration and deceleration.
- Five raster scene plates are reused across the fifteen shots.
- The human and mechanical agent never perform an action. Camera scaling, text reveals, and overlays move, but the subjects remain still.

The rebuild must therefore change both the scene count and the ownership of motion. A different renderer alone would not fix the problem.

## Approaches considered

### 1. Fully generative image-to-video

Animate every plate with a local diffusion model and edit the resulting clips.

Advantages: visible character motion and organic camera behavior.

Risks: facial drift, broken engraving lines, inconsistent identity, long iteration time, and the exact “AI slop” failure the film must avoid. The available RTX 3070 has 8 GB VRAM, so local generation is possible with memory-efficient models but not cheap enough to make every scene generative.

### 2. Fully controlled 2.5D/WebGL

Cut the existing plates into depth layers and animate them with Three.js, GSAP, masks, particles, and vector geometry.

Advantages: deterministic, sharp, art-directable, and identity-safe.

Risks: convincing camera depth and environmental animation are straightforward, but nuanced human turning or hand articulation can still read as a puppet.

### 3. Hybrid performance film — selected

Use image-to-video only for the two moments that require organic subject performance. Build the rest as controlled Three.js/GSAP animation inside HyperFrames.

This provides visible human/agent movement while keeping the typography, transitions, archive vortex, mechanical aperture, mirror distortion, particles, and final lockup deterministic. Any generated clip that changes facial identity, melts engraving lines, or introduces unstable anatomy is rejected and replaced by controlled 2.5D animation.

## Locked film structure

The new cut has five scenes and no montage of one-second cards.

### Scene 1 — The aperture, 0.0–3.6 seconds

The film begins inside a mechanical iris. Concentric bronze rings rotate on separate depth planes while engraved dust crosses the lens. The aperture opens and the camera travels through it into the mirror chamber. This is a continuous 3D move, not a cut between eye pictures.

### Scene 2 — The delayed mirror, 3.2–8.0 seconds

The Roman human and bronze agent occupy one continuous chamber. They breathe and turn with a visible half-beat delay, then synchronize. The mirror surface ripples between them. “YOUR AI FORGETS YOU” is engraved into the glass and displaced by the ripple rather than placed as a title card.

This is the first quality-gated image-to-video hero clip. Its subject identity must remain stable throughout.

### Scene 3 — Contact, 7.6–11.2 seconds

Human and mechanical hands begin separated, move toward each other, make contact, and compress the mirror surface. Light travels outward from the fingertip through etched circuitry.

This is the second quality-gated hero clip or a controlled two-hand puppet if generation fails. The action must be unmistakable at normal playback speed.

### Scene 4 — Memory becomes structure, 10.8–16.4 seconds

The contact pulse becomes a real 3D manuscript vortex. Individual pages spiral past the camera at different depths. Repeated traits — PROOF, TASTE, SCOPE, DONE — appear as ink on moving sheets. The pages converge and physically fold into a `you.md` artifact. “YOUR HISTORY DOESN’T” travels on the vortex wall rather than appearing on a separate slide.

### Scene 5 — One identity, 16.0–20.0 seconds

The `you.md` artifact enters the agent’s chest mechanism. The human and agent turn in the same motion, their engraved contours collapse into the Ditto mark, and the final line resolves: “STOP STARTING FROM ZERO.” The last readable state holds for 1.25–1.5 seconds while subtle paper grain and seal pressure continue.

## Transition and camera rules

- Maximum four scene transitions.
- Scenes overlap by 0.3–0.5 seconds using match movement, mirror distortion, or object continuity.
- One hard impact cut is allowed at the hand contact only.
- Camera velocity must carry through scene boundaries. No repeated zoom-in/reset pattern.
- The same subject transform may not be split into multiple eased segments unless a visible physical impact motivates the velocity change.
- No static interval longer than 0.5 seconds except the final readability hold.

## Animation ownership

Every scene must contain subject-owned motion, not only camera motion.

- Aperture: ring rotation, iris opening, dust depth travel.
- Mirror: breathing, head/shoulder movement, delayed agent response, surface ripple.
- Contact: two independently moving hands, fingertip compression, circuit-light propagation.
- Archive: pages with individual 3D trajectories, ink drawing, artifact folding.
- Brand: synchronized turn, contour collapse, seal emboss, living grain.

## Technical architecture

- HyperFrames remains the master compositor and timing contract.
- GSAP owns the single seek-safe master timeline.
- Three.js owns the aperture, mirror shader, page field, particles, and depth camera.
- Generated hero clips are ordinary timed media layers inside the composition.
- The final film remains deterministic at any requested frame.
- Remotion is not introduced because its animation primitives do not solve missing source performance, and adding a second compositor would increase risk without improving the result.

## Local generation strategy

The workstation has an RTX 3070 with 8 GB VRAM and 32 GB system RAM. The preferred local path is a memory-efficient image-to-video model through the existing ComfyUI installation. The first test uses a short, low-motion hero clip at production aspect. Only accepted clips are upscaled/interpolated and included.

Generation is a gated input, not the editing system:

1. Generate a 3–4 second mirror-performance proof.
2. Reject on any identity drift, anatomy break, texture melting, or temporal flicker.
3. If accepted, generate the contact proof.
4. If rejected, use the deterministic 2.5D puppet fallback.

## Acceptance criteria

### Motion continuity

- Exactly five scenes.
- No more than five detected high-energy scene boundaries.
- Uniform 60 fps output with exactly 1,200 frames.
- No duplicate-frame run longer than 0.25 seconds before the final hold.
- No unexplained optical-flow spike at a transition.

### Visible animation

- Both human and agent visibly change pose in the mirror scene.
- Both hands visibly travel before contact.
- At least twelve independent pages cross depth planes in the archive scene.
- The aperture and mirror distortion are visibly animated without relying on camera scale.
- The `you.md` artifact visibly assembles or folds.

### Quality

- Human and agent identities remain stable.
- No malformed anatomy, face warping, crawling engraving lines, or generative text.
- No PowerPoint-style card changes.
- Final copy remains readable for at least 1.25 seconds.
- H.264, 1920×1080, 60 fps, AAC stereo, 20.000 seconds, no voiceover.

## Verification

- HyperFrames lint and runtime validation.
- Keyframe/onion proof for the aperture, mirror subjects, both hands, and archive pages.
- Direct frame samples at every scene boundary and action peak.
- Encoded-video scene-boundary, duplicate-frame, black-frame, codec, frame-count, and loudness checks.
- Side-by-side review against the rejected V1 contact sheet to confirm fewer cuts and subject-owned motion.

