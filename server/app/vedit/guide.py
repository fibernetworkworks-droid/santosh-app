TIMELINE_GUIDE = r"""
VEDIT TIMELINE (JSON) - how to describe an edit
================================================
All paths are relative to the workspace folder. Times: seconds (12.5), "MM:SS", "HH:MM:SS.mmm", or "120f" (frames).
Every time is snapped to the output frame grid, so cuts are frame-exact.

{
  "output": {                      // all optional; defaults come from the first video clip
    "aspect": "9:16",              // 9:16 | 16:9 | 1:1 | 4:5 | 4:3  (or give width + height)
    "width": 1080, "height": 1920,
    "fps": 30,                     // 24, 25, 30, 60, "30000/1001" ...
    "fit": "blur",                 // crop (fill frame) | pad (black bars) | blur (blurred bars)
    "crf": 18,                     // quality: 18 visually lossless, 23 smaller files
    "preset": "veryfast",          // x264 speed/size trade-off
    "codec": "h264",               // h264 | hevc
    "loudnorm": true               // or {"I": -14}  -> two-pass EBU R128 loudness (-14 LUFS = social media)
  },
  "clips": [                       // played in order
    {"src": "raw/intro.mp4", "in": "00:00:03.2", "out": 9.0,
     "speed": 1.0,                 // 0.25 to 4 (audio pitch kept)
     "volume": 1.0, "mute": false,
     "fade_in": 0.3, "fade_out": 0.3,
     "crop": {"x": 420, "y": 0, "w": 1080, "h": 1080},   // manual crop in source pixels (before fit)
     "fit": "crop",                // per-clip override
     "texts": [{"text": "Day 1 in Goa", "start": 0.5, "end": 3, "position": "bottom", "fade": 0.3}],
     "transition": {"type": "fade", "duration": 0.5}     // into the NEXT clip
    },
    {"src": "photos/beach.jpg", "duration": 3},          // still image
    {"color": "#101828", "duration": 2, "texts": ["Follow for more"]}  // title card
  ],
  "texts": [ {"text": "@newtika", "position": "top-left", "size": 40, "box": false} ],  // on the whole video
  "overlays": [ {"src": "brand/logo.png", "position": "top-right", "scale": 0.15, "opacity": 0.9} ],
  "music": {"src": "music/bg.mp3", "volume": 0.25, "duck": true, "fade_out": 2, "loop": true},
  "subtitles": {"src": "captions.srt", "style": {"Fontsize": 14, "MarginV": 60}, "font": "fonts/NotoSansDevanagari-Bold.ttf"}
}

Text item fields: text, start, end (seconds within the clip, or the whole video for top-level "texts"),
position (top-left top top-right left center right bottom-left bottom bottom-right), size (px, 0 = auto),
color, box (true/false), box_color (e.g. "black@0.55"), fade (s), font (.ttf path), x + y (exact pixel position of the
top-left corner, instead of position). Long text wraps automatically. Text is drawn with libass, so Hindi, Marathi,
Tamil, Bengali, Gujarati, Arabic etc. are shaped correctly when the font has those letters.

Transitions: fade dissolve fadeblack fadewhite wipeleft wiperight wipeup wipedown slideleft slideright slideup
slidedown circleopen circleclose radial smoothleft smoothright smoothup smoothdown pixelize zoomin distance
hblur squeezeh squeezev diagtl diagtr diagbl diagbr. A transition overlaps the two clips, so the video gets
shorter by its duration.

Subtitle style keys are ASS style names: Fontname, Fontsize (in 288-line units: 14-18 fits vertical video),
PrimaryColour (&H00BBGGRR), OutlineColour, Outline, Shadow, Bold, Alignment (2 bottom centre, 8 top centre),
MarginV. Hindi/Marathi/other Indian scripts need a font that has them, e.g. Noto Sans Devanagari.

WORKFLOW FOR RELIABLE EDITS
1. probe every source (duration, fps, size, audio?).  2. Plan; for talking-head use find_silence / remove_silence;
   for montages use find_scenes.  3. validate_timeline.  4. render_timeline - read the report: ok must be true.
5. contact_sheet the result and look at it before telling the user it is done.
"""
