# Vendored site libraries (served from the site itself, never a CDN)

- `lottie_light.min.js` = lottie-web 5.13.0 `build/player/lottie_light.min.js` (MIT, Airbnb) with a one-line version
  banner added so the safety gates can check it against OSV. Light build = SVG renderer, no expressions, no eval.
- `three-hero.js` = Hoola's house 3D scenes (`../src/hero3d.src.js`, MIT, Newtika) bundled with the parts of three.js
  r187 (MIT) they import. Rebuild:

      npm i esbuild@0.25.5 three@0.187.0
      npx esbuild ../src/hero3d.src.js --bundle --minify --format=esm --target=es2020 --legal-comments=none \
        --banner:js='/*! Hoola 3D hero (MIT, Newtika) + three.js r187 (MIT, three.js authors) - https://threejs.org/ */' \
        --outfile=three-hero.js

  The file name must NOT start with `hoola-`: the library gate skips Hoola's own scripts, and this one carries three.js.
