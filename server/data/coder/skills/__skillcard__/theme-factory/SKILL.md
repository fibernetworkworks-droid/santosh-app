---
name: theme-factory
description: Toolkit for styling artifacts with a theme. These artifacts can be slides, docs, reportings, HTML landing pages, etc. There are 10 pre-set themes with colors/fonts that you can apply to any artifact that has been creating, or can generate a new theme on-the-fly.
imported: true
when_to_use: theme lagao, colours aur fonts choose karo, slides ko style karo, deck ka look, brand colours, palette, website ka theme, report ka design, new theme banao
license: Complete terms in LICENSE.txt
---
# Theme Factory Skill

This skill provides a curated collection of professional font and color themes themes, each with carefully selected color palettes and font pairings. Once a theme is chosen, it can be applied to any artifact.

## Purpose

To apply consistent, professional styling to presentation slide decks, use this skill. Each theme includes:
- A cohesive color palette with hex codes
- Complementary font pairings for headers and body text
- A distinct visual identity suitable for different contexts and audiences

## Usage Instructions

To apply styling to a slide deck or other artifact:

1. **Show the theme showcase**: Display the `theme-showcase.pdf` file to allow users to see all available themes visually. Do not make any modifications to it; simply show the file for viewing.
2. **Ask for their choice**: Ask which theme to apply to the deck
3. **Wait for selection**: Get explicit confirmation about the chosen theme
4. **Apply the theme**: Once a theme has been chosen, apply the selected theme's colors and fonts to the deck/artifact

## Themes Available

The following 10 themes are available, each showcased in `theme-showcase.pdf`:

1. **Ocean Depths** - Professional and calming maritime theme
2. **Sunset Boulevard** - Warm and vibrant sunset colors
3. **Forest Canopy** - Natural and grounded earth tones
4. **Modern Minimalist** - Clean and contemporary grayscale
5. **Golden Hour** - Rich and warm autumnal palette
6. **Arctic Frost** - Cool and crisp winter-inspired theme
7. **Desert Rose** - Soft and sophisticated dusty tones
8. **Tech Innovation** - Bold and modern tech aesthetic
9. **Botanical Garden** - Fresh and organic garden colors
10. **Midnight Galaxy** - Dramatic and cosmic deep tones

## Theme Details

Each theme is defined in the `themes/` directory with complete specifications including:
- Cohesive color palette with hex codes
- Complementary font pairings for headers and body text
- Distinct visual identity suitable for different contexts and audiences

## Application Process

After a preferred theme is selected:
1. Read the corresponding theme file from the `themes/` directory
2. Apply the specified colors and fonts consistently throughout the deck
3. Ensure proper contrast and readability
4. Maintain the theme's visual identity across all slides

## Create your Own Theme
To handle cases where none of the existing themes work for an artifact, create a custom theme. Based on provided inputs, generate a new theme similar to the ones above. Give the theme a similar name describing what the font/color combinations represent. Use any basic description provided to choose appropriate colors/fonts. After generating the theme, show it for review and verification. Following that, apply the theme as described above.

<!-- HOOLA NOTE: everything below this line was added by Newtika for Hoola. The text above is Anthropic's original (Apache License 2.0, see LICENSE.txt); only the frontmatter line when_to_use was added. -->

## Hoola note (Modified by Newtika for Hoola, 4 Nov 2026)
- Do not try to "display theme-showcase.pdf": it ships with this skill but is a binary file that `read_file` cannot open. Instead read the theme files with `skill_manage read_file` (`themes/<name>.md`) and show her the 10 names with their 4 colours as a short list, then ask which one.
- Apply a chosen theme through Hoola's own tools: `doc_studio` / HOOLA PRINT for documents and PDFs, the website builder (`website`) and Create Studio for pages and posters, or the artifact tools for an HTML page. Use the hex codes exactly.
- The fonts named in a theme file (DejaVu etc.) may not exist in the target tool. Use the closest font that tool really has and tell her which one you used. For Hindi or Marathi text pick a family with Devanagari (for example Noto Sans Devanagari) so the letters do not break.
- If she has a brand kit saved in Hoola, her brand colours come first; offer a theme only when she has none or asks.
- Check contrast (dark text on light, light on dark) before you say it is done. Say "ye theme lagaya" only after it is applied.
- Hoola's own house rules win over this skill if they ever disagree.
