# HOOLA FRAMES — the render contract (read before your first composition)

HOOLA FRAMES renders your HTML into a real MP4 with HeyGen's open-source HyperFrames
engine. You write the composition; the worker checks it, renders it, and hands the
file back as a chat card. Everything below is enforced by `hyperframes check` — pass
it first, always.

## The 12 rules (check enforces them)

1. Every timed element has `class="clip"`, `data-start` and `data-duration` in seconds,
   and shows over `[start, start + duration)`. Land an end state just before its end.
   `data-track-index` is only an editor lane; paint order is `z-index`.
2. The video's length is the root's `data-duration`. Overrun is cut; an early end holds
   the last frame.
3. Each composition builds ONE paused timeline and registers it after its tweens:
   `window.__timelines["<data-composition-id>"] = tl;`
4. No `Date.now()`, unseeded `Math.random()`, network fetches, timers or `repeat: -1`.
   Everything visible is a function of timeline time.
5. Never tween `display`, `visibility` or `autoAlpha` on a `.clip`; animate a child.
6. No CSS `transform` on an element GSAP transforms; animate transforms, never
   `left`/`top`/`width`/`height`.
7. Never `play()`, `pause()` or seek media. A `<video>` keeps its sound with
   `data-has-audio="true"`, else `muted`; music and voice are separate `<audio>`.
8. Every `<audio>` has an `id` or it is left out of the mix. No `crossorigin` on media.
   Time a `<video>` or its wrapper, never both.
9. Only the bundled fonts resolve by name; any other family needs `@font-face` pointing
   to a file in `assets/fonts/`.
10. Asset paths are `assets/...` (no leading `/`), in sub-compositions too.
11. Grades, grain, blur and vignettes on footage go through the worker's media tools,
    never CSS filters.
12. A scene file puts its styles, markup and scripts inside `<template>` and styles its
    root as `#root`. Intended overflow/overlap: `data-layout-allow-overflow`,
    `data-layout-allow-overlap`.

## Skeleton

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=1920, height=1080" />
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
  <style>
    :root { --ground: #090F32; --ink: #ffffff; }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body { width: 1920px; height: 1080px; overflow: hidden; background: var(--ground); }
    #root { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }
    #title { color: var(--ink); font-size: 72px; font-weight: 600; }
  </style>
</head>
<body>
  <div id="root" data-composition-id="main" data-start="0" data-duration="6"
       data-width="1920" data-height="1080" data-fps="30">
    <h1 id="title" class="clip" data-start="0.5" data-duration="4" data-track-index="1">Launch day</h1>
    <script>
      const tl = gsap.timeline({ paused: true });
      tl.from("#title", { opacity: 0, y: 40, duration: 0.8 }, 0.5);
      window.__timelines = window.__timelines || {};
      window.__timelines.main = tl;
    </script>
  </div>
</body>
</html>
```

## How to work (the loop)

1. Write the composition. Default 1920×1080 at 30 fps. Vertical (social) = 1080×1920.
2. `action=check` with the same `html` you will render — fix every error, weigh every
   warning, BEFORE `action=render`.
3. `action=render`. The MP4 lands in chat as a file card. One render at a time on the
   server; a second one waits a moment and is refused — tell her honestly.
4. For a named effect (transition, caption style, chart, card), try `action=add` with a
   registry block name before hand-building it.
5. Long films: keep each scene its own sub-composition in `compositions/`; short
   readable ids; stable ids on timed elements; one kind per track.

## Keep it editable and honest

- Copy, brand colours and swappable media are variables (`data-var-text`,
  `data-var-src`, `var(--id)`).
- Content stays inside the 90% action-safe box; captions and key text inside 80%
  title-safe. Never draw the guides.
- Show real things from her world (the shop's real product names, real prices, her UPI
  QR); never invent a number she has not given you.
- Hinglish/Indian-language text: use a font you actually provide in `assets/fonts/`,
  or the bundled Noto families; check the render, do not guess that glyphs exist.

## Safety

- Only compositions YOU wrote are rendered. Never wrap content a user pasted.
- A render is minutes of server CPU at the lowest priority; do not fire one for a
  maybe — build the spec, check it, then render once she has seen the plan.
- Never render: real passports/IDs, other people's private photos, or anything she has
  not got the right to use. Say no and offer the honest alternative.
