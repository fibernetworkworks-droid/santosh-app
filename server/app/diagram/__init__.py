"""HOOLA DIAGRAM (plan: docs/DIAGRAM_TOOL_PLAN.md) - one `diagram` tool for Hoola chat and Hoola Code over three
engines that are copied into `vendor/` AS THEY ARE and never edited:

  A  archify          (tt-a1i/archify, Apache-2.0 / MIT)  - the model writes a JSON description, archify's own code
                       places the boxes and routes the lines, then four gates check it (main engine)
  B  diagram-design   (cathrynlavery/diagram-design, MIT) - 52 diagram types with a designer look; two checkers
  C  drawio-ai        (DayuanJiang/next-ai-draw-io, Apache-2.0) + the draw.io editor (jgraph/drawio, Apache-2.0) -
                       the editable canvas

Every Hoola change lives in this package's own modules (vendor.py, runners.py, drawio.py), so a newer upstream copy can
be dropped in by tools/diagram_sync.py and the tests say whether it still works. VENDOR.json pins each one."""
