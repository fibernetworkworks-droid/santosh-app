---
name: fe-frames-templates
description: HyperFrames MP4 template packs - charts + motion, cheap
when_to_use: video, reel, reels, animated video, chart video, sales video, short video, motion graphics, explainer video, mp4
---
GOAL: a new MP4 style is ASSEMBLED, not invented - pick a proven template block from
this pack, swap her content in, check cheap, render once. Writing from scratch every
time breaks the check gate and eats render minutes.

THE TEMPLATE PACKS (pick by ask):
- CHART PACK (when numbers must be shown): big-number KPI card (one number + label + delta);
  CSS bar chart (flex rows, width % = value); SVG polyline line/area chart (points
  pre-computed, stroke-dasharray draw-on); donut progress ring (SVG circle,
  stroke-dashoffset). When there are numbers, use these blocks first.
- MOTION PACK (when a scene must move): kinetic type (words fade/rise one by one,
  stagger 80-120ms); lower-third (name + title, slide-in from left, bottom safe zone);
  logo sting (scale 0.9->1 + fade, 600ms); price/offer reveal (the number pops from
  a blur/seal); countdown strip; gradient wash background (the house gradient, slow drift).
- LAYOUT DISCIPLINE (CSS): 16:9 = 1920x1080, 9:16 = 1080x1920; safe margins ~10%
  on every edge (WhatsApp/Insta UI cuts it off); centre with flex/grid; one scene
  one idea - text 6 to 12 words per screen.

THE LAWS:
- ALL INLINE: no CDN, no webfont fetch, no network during render - the determinism
  gate (`frames check`) refuses it. Fonts = system stack; icons = inline SVG or emoji.
- CHECK FIRST (cheap), RENDER AFTER (expensive): only when hoola_frames action=check
  passes, then action=render. Check errors come in the lint/runtime/layout/motion/
  contrast/craft sections - fix them and check again.
- Colors and motion from Hoola's UI kit (read the skill fe-ui-kit) - one family,
  every video must be recognisable.
- Assets project-relative only (assets/..., compositions/...); never an outside path.
- Only existing doors: hoola_frames actions (render/check/timeline/snapshot/add/
  status/avatar_film). No Chrome/FFmpeg of your own.
NEVER: network fetch mid-render; unseeded Math.random/wall clock in the composition
(the gate rejects it); more than 3 ideas in one scene; render without a check.
