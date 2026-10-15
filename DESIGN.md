---
name: GainGuard
description: A daylight measurement workbench for ultrasound model-reliability research.
colors:
  paper: "#f6f8f5"
  white: "#fff"
  ink: "#1b302a"
  muted: "#5c6c64"
  line: "#dce3dc"
  green: "#256c57"
  forest: "#123c34"
  soft: "#eaf0e8"
  amber: "#855112"
  amber-bg: "#fbf0d8"
  red: "#a04435"
typography:
  display:
    fontFamily: '"Public Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "clamp(28px, 2.75vw, 42px)"
    fontWeight: 600
    lineHeight: 1.14
    letterSpacing: "-0.04em"
  title:
    fontFamily: '"Public Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "14px"
    fontWeight: 650
    letterSpacing: "-0.2px"
  body:
    fontFamily: '"Public Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "12px"
    lineHeight: 1.7
  label:
    fontFamily: '"Public Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "11px"
  measurement:
    fontFamily: 'Consolas, "Courier New", monospace'
    fontSize: "12px"
rounded:
  badge: "4px"
  field: "6px"
  button: "7px"
  image: "8px"
  panel: "12px"
spacing:
  compact: "8px"
  control: "12px"
  inset: "16px"
  panel: "20px"
  section: "24px"
components:
  button-primary:
    backgroundColor: "{colors.forest}"
    textColor: "{colors.white}"
    rounded: "{rounded.button}"
    padding: "12px 15px"
  button-outline:
    textColor: "{colors.ink}"
    rounded: "{rounded.button}"
    padding: "12px 15px"
  button-text:
    textColor: "{colors.green}"
    padding: "4px 0"
  input-search:
    backgroundColor: "{colors.white}"
    rounded: "{rounded.field}"
    padding: "8px 9px"
  queue-count:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.forest}"
    rounded: "{rounded.badge}"
    padding: "2px 5px"
  review-panel:
    backgroundColor: "{colors.amber-bg}"
    rounded: "{rounded.panel}"
    padding: "20px"
---

# Design System: GainGuard

## Overview

**Creative North Star: "The daylight measurement workbench"**

GainGuard uses the user-approved light measurement-workbench direction: quiet green-tinted paper, dark green operational controls, real ultrasound imagery and explicit numeric results. Its character is precise, restrained and dense enough for research. Public Sans supports both the large question-led headings and compact controls; monospace values separate measurements from explanatory prose.

This record describes the shipped dependency-free interface in `web/index.html`, `web/styles.css` and `web/app.js`. It covers shared visual behavior across the experiment, benchmark, queue and methods views. The chosen world is recorded in `docs/direction.md`; no generated comp or catalog QUALITY BAR card was selected. The supplied desktop and mobile frames in `docs/evidence/` were extracted from compressed native recordings because native screenshot capture failed. They support broad composition checks; fine rendered detail is not fully verified. Exact tokens below come from source, including its final readability overrides.

**Key Characteristics:**

- Light, flat surfaces separated by fine rules and tonal fields.
- Dark real-image fields with matched comparison geometry.
- Green actions and measurements; amber review attention and red model-error markers.
- Plain text explanations beside exact values and units.

## Colors

The palette is a green-tinted neutral foundation with operational green and semantic amber/red accents. Frontmatter preserves the CSS custom-property names and canonical values; it is the source for color values.

### Primary

- **Operational green** (`green`): links, selected navigation rules, chart trajectories and ordinary probability bars.
- **Deep forest** (`forest`): primary buttons, active navigation text, range controls and prominent report surfaces.

### Secondary

- **Review amber** (`amber`, `amber-bg`): dirty-control attention and review-panel background. The panel uses darker related amber text values locally; those are not a separate global palette.
- **Error red** (`red`): known clean-model error dots, error probability bars and error messages.

### Neutral

- **Daylight paper** (`paper`): application background.
- **White** (`white`): header, footer and input surfaces.
- **Soft sage** (`soft`): queue runner and count badge.
- **Deep green ink** (`ink`): primary text and numeric outputs.
- **Muted green grey** (`muted`): secondary explanations and chart labels.
- **Pale divider** (`line`): structural borders and row separators.

**The State Has Meaning Rule.** Green, amber and red carry operational or result meaning; preserve their text labels and reasons so color is never the only state cue.

## Typography

**Display and body font:** self-hosted Public Sans, with the platform sans-serif fallbacks recorded above.
**Measurement font:** Consolas, Courier New, monospace.

The ramp is deliberately compact rather than a geometric scale. Large, tightly tracked headings frame the task; mid-size section titles organize the workspace; small text supports dense research content. The final stylesheet overrides supersede earlier smaller control and result sizes.

### Hierarchy

- **Display:** the frontmatter display role serves experiment headings; report and methods headings use a fixed desktop size (38px). Narrow-screen experiment headings use (34px), and report/methods headings use (32px).
- **Section title:** shared small section headings use the title role; report section headings use (17px, weight 600).
- **Body:** control explanations, review reasons and queue descriptions use (12px); methods prose is roomier (13px, line-height 1.85), reducing to (12px) on narrow screens.
- **Label:** secondary chart notes and metadata generally use (10–11px); actionable buttons use (12px), with compact queue actions using (10px) on narrow screens.
- **Measurement:** use monospace for sample IDs, control outputs, probabilities, chart numerals and table values. Tables additionally use tabular numerals. Large result and benchmark values have their own context sizes rather than a universal display token.

**The Readable Result Rule.** Inherit the final control/result sizing, not the obsolete small sizes earlier in the stylesheet. Keep values, units, dataset labels and model-output labels distinct.

## Layout

The desktop shell has a white header (82px) above a short research notice. The experiment workspace uses a sample rail (210px) and flexible main region, whose normal padding is (34px 34px 22px). The comparison and controls use a flexible image area plus a control column (224px), separated by a gap (24px). Image fields remain paired in equal-width columns. Result panels follow on a divided row; they are not floating overlays.

At a maximum width (1100px), the rail narrows to (185px); controls move below the images into three columns. At a maximum width (760px), the rail becomes a horizontal sample strip, navigation wraps onto its own scrollable row, workspace side padding becomes (20px), result panels and report columns stack, and controls retain grouped labels above their sliders. Benchmark tables retain an explicit minimum width (880px) inside horizontal overflow. At a minimum width (1550px), the rail and controls widen to (230px) and (260px).

Shared report and methods views use a centered maximum width (1520px). Methods copy is capped at (75ch), with a sticky side index on desktop and wrapped inline links on mobile. Spacing uses compact increments around controls and larger gaps between sections; the frontmatter records recurring steps, not a newly imposed universal grid.

**The Comparison Geometry Rule.** Give original and stressed images equal fields and the same containment treatment so visual changes can be compared directly.

## Elevation & Depth

The shipped interface uses no box shadows. Depth comes from white chrome, pale sidebar and panel tones, thin borders, dark scan fields and solid forest actions. Selected samples use a tinted fill plus a border. Focus is a visible sage outline (3px) offset by (4px), independent of surface depth.

**The Flat Workbench Rule.** Use tonal fields and dividers for hierarchy; preserve the flat surface grammar of the shipped workbench.

## Shapes

Panels use gently rounded corners through the shared panel radius. Images and selected sample rows have the smaller image radius; buttons and fields use their own closely related radii. Fine borders, generally (1px), define fields and structural divisions. Badges and numeric-output chips are compact rectangles; dots and loading indicators are circular. These distinctions come from the build rather than a single radius applied everywhere.

## Components

### Buttons

Compact, explicit actions. Primary and outline buttons share (12px 15px) padding, (40px) minimum height, semibold text (weight 600) and small SVG icons. Primary buttons use forest with white text; hover changes the forest background and applies the shared slight brightness reduction. Outline buttons use a muted green border and transparent background. Text actions are green with a hover underline. Disabled buttons use reduced opacity (0.55) and a wait cursor. All actionable elements retain the visible focus outline.

Button color transitions last (160ms). Probability bars animate their horizontal scale over (350ms) with a decelerating curve; image filters transition over (250ms). Reduced-motion preference removes animation and transition.

### Chips

Queue counts use soft sage, forest text and the compact badge radius. Slider outputs use a pale green inset with monospace numbers. These convey counts or readings, not pill-shaped navigation filters.

### Cards / Containers

Review results use the shared panel radius and panel padding, amber attention fill, an explicit SVG status icon, reasons, and a divided pair of measurements. The stable variant changes to a pale green field and states that stability can still be wrong. Queue runners use soft sage with the same panel radius. Report findings use forest. Ordinary report sections rely on dividers rather than placing every section in a card.

### Inputs / Fields

Search and select fields use white fill, pale borders and the field radius. Search combines a small outlined SVG with an unbordered native search input inside the field. Range inputs retain native interaction with forest accent color; every slider has its own label, output, endpoint labels and an explicit run action. Changed settings receive amber status text. Errors use a pale red panel with explanatory text.

### Navigation

Desktop navigation uses muted semibold text and a green bottom rule for the current page; forest text reinforces the active state. The queue count remains beside its label. Mobile navigation occupies a separate row with horizontal overflow. Methods navigation becomes a wrapped inline index on mobile. Outbound-style actions use the consistent inline SVG arrow rather than text glyphs.

### Paired image measurement

Two dark, rounded fields contain the actual original and transformed ultrasound images with `object-fit: contain`. Captions, model-output names, probability bars and numerical values sit outside the image field. Red probability bars distinguish known incorrect outputs. SVG charts use green trajectories, muted labels and pale grid lines; text explains the measured quantity and review condition.

## Do's and Don'ts

### Do:

- **Do** preserve equal geometry for paired images and keep measured outputs attached to their image.
- **Do** use Public Sans for prose and interface text, with monospace measurements and explicit units.
- **Do** retain text labels, review reasons and visible keyboard focus alongside semantic color.
- **Do** use flat tonal panels and fine dividers, with responsive stacking and explicit table overflow.

### Don't:

- **Don't** replace real ultrasound evidence with decorative imagery.
- **Don't** collapse dataset truth, model output and review status into one undifferentiated label.
- **Don't** inherit the earlier tiny control/result declarations instead of the final readable overrides.
- **Don't** add clinical visual theater to the user-approved research workbench.

Not canonized: the tiny in-image scan annotations (5–7px in source) remain a legibility limitation, not a reusable label role; the unused lime custom property and isolated local color adjustments are not system tokens.
