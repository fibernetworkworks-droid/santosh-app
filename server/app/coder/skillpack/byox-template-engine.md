---
name: byox-template-engine
description: Build a template engine: tags, loops, conditionals, inheritance
---
GOAL: a Jinja2-like template engine with inheritance that auto-escapes HTML.

PHASES
1. Split template into text spans and {{ expr }} tokens (regex or manual scan).
2. Render: replace {{ name }} by looking up `name` in a context dict.
3. {% if cond %}...{% endif %} with truthy evaluation (False, 0, [], "" = falsy).
4. {% for item in list %}...{% endfor %} loop with loop.index.
5. Template inheritance: {% extends "base.html" %} + {% block name %}.

CORE CONCEPTS
- Tokenise in two passes: first split by {%…%} and {{…}}, then lex each tag.
- Context chain: a child template's context shadows the parent's for block override.
- Auto-escaping: replace &, <, >, " in expression output; mark safe strings with Markup().

VERIFY: extends + block override renders correctly; XSS `<script>` auto-escaped.
