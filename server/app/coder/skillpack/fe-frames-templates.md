---
name: fe-frames-templates
description: HyperFrames MP4 template packs - charts + motion, cheap
when_to_use: video, reel, reels, animated video, chart video, sales video, short video, motion graphics, explainer video, mp4
---
GOAL: a new MP4 style is ASSEMBLED, not invented - pick a proven template block from
this pack, swap her content in, check cheap, render once. Har baar scratch se likhna
check-gate todta hai aur render minutes kha jaata hai.

THE TEMPLATE PACKS (pick by ask):
- CHART PACK (numbers dikhaana hai): big-number KPI card (ek number + label + delta);
  CSS bar chart (flex rows, width % = value); SVG polyline line/area chart (points
  pre-computed, stroke-dasharray draw-on); donut progress ring (SVG circle,
  stroke-dashoffset). Numbers ho to pehle yehi blocks.
- MOTION PACK (scene move karani hai): kinetic type (words ek-ek karke fade/rise,
  stagger 80-120ms); lower-third (naam + title, slide-in from left, bottom safe zone);
  logo sting (scale 0.9->1 + fade, 600ms); price/offer reveal (blur/seal se number
  pop); countdown strip; gradient wash background (the house gradient, slow drift).
- LAYOUT DISCIPLINE (CSS): 16:9 = 1920x1080, 9:16 = 1080x1920; safe margins ~10%
  har kinare par (WhatsApp/Insta UI kaat deta hai); flex/grid se center; ek scene
  ek idea - text 6 se 12 words per screen.

THE LAWS:
- SAB INLINE: no CDN, no webfont fetch, no network during render - the determinism
  gate (`frames check`) refuses it. Fonts = system stack; icons = inline SVG ya emoji.
- CHECK PEHLE (cheap), RENDER BAAD MEIN (expensive): hoola_frames action=check pass
  ho tabhi action=render. Check errors lint/runtime/layout/motion/contrast/craft
  sections mein aate hain - unhe theek karke dobara check.
- Colors aur motion Hoola ke UI kit se (skill fe-ui-kit read karo) - ek family,
  har video pehchani jaani chahiye.
- Assets project-relative hi (assets/..., compositions/...); bahar ka path kabhi nahi.
- Sirf existing doors: hoola_frames actions (render/check/timeline/snapshot/add/
  status/avatar_film). Koi apna Chrome/FFmpeg nahi.
NEVER: network fetch mid-render; unseeded Math.random/wall clock in the composition
(gate reject karta hai); ek scene mein 3 se zyada ideas; render bina check ke.
