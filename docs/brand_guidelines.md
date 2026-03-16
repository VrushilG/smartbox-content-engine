# Brand Guidelines — Smartbox Content Engine

## About Smartbox

Smartbox Group is Europe's leading experience gift company, headquartered in Dublin, Ireland. We sell moments — weekends away, spa days, adventure experiences, and culinary journeys — packaged as gift boxes. Our brand is warm, optimistic, and human.

---

## Design tokens

All tokens are defined as CSS custom properties in `frontend/src/css/main.css`. Never hardcode hex values anywhere else in the codebase.

### Colour palette

| Token | Value | Usage |
|-------|-------|-------|
| `--color-coral` | `#E8593C` | Primary CTA, progress fill, active borders, icons |
| `--color-coral-hover` | `#D14A2E` | Hover state for coral elements |
| `--color-coral-tint` | `#FFF0EC` | Subtle backgrounds on hover, pills, file info |
| `--color-navy` | `#1A1A2E` | Header, hero, dark sections |
| `--color-dark-surface` | `#2D2D44` | Card backgrounds on dark sections |
| `--color-warm-white` | `#F9F6F2` | Page background — never pure white |
| `--color-text-primary` | `#1A1A2E` | Body text on light backgrounds |
| `--color-text-muted` | `#6B6B80` | Secondary text, hints, labels |
| `--color-text-on-dark` | `#F9F6F2` | Text on navy/dark-surface backgrounds |

### Typography

- **Font family**: Inter (Google Fonts CDN, weights 400/500/600 only)
- **Base size**: 16px
- **Line height**: 1.6 for body, 1.2 for headings
- **Weight scale**: regular (400), medium (500), semibold (600)

### Spacing

Uses an 8-point grid via CSS custom properties (`--space-1` = 0.25rem through `--space-16` = 4rem).

### Border radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | `4px` | Badges, small elements |
| `--radius-md` | `8px` | Buttons, banners |
| `--radius-lg` | `12px` | Cards |
| `--radius-full` | `9999px` | Pills, progress bar |

---

## Component specifications

### CTA button
- Background: `var(--color-coral)`
- Text: white
- Border radius: `var(--radius-md)` (8px)
- No border
- Hover: `var(--color-coral-hover)`
- Disabled: opacity 0.45, `cursor: not-allowed`
- Label: **"Generate Content"** (never "Submit", "Process", "Upload")

### Category pills
- Background: `var(--color-coral-tint)`
- Text: `var(--color-coral)`
- Border radius: `var(--radius-full)` (fully rounded)
- Text transform: capitalize

### Asset cards
- Background: `var(--color-dark-surface)`
- Border radius: `var(--radius-lg)` (12px)
- Shadow: `var(--shadow-md)`
- Content text: `var(--color-text-on-dark)`
- Label text (section headers): `var(--color-text-muted)`, uppercase, letter-spacing

### DAM filename badge
- Font: monospace
- Text: `var(--color-text-muted)`
- Background: `rgba(255, 255, 255, 0.06)` — subtle translucent tint
- Padding: `--space-2` × `--space-3`
- Border radius: `var(--radius-sm)`

### Progress bar
- Track: `var(--color-border)`
- Fill: `var(--color-coral)`
- Height: 8px
- Border radius: `var(--radius-full)`
- Transition: smooth width animation

### Drag-and-drop upload zone
- Border: 2px dashed `var(--color-coral)`
- Background default: white
- Background hover/active: `var(--color-coral-tint)`
- Border radius: `var(--radius-lg)`

---

## Brand voice

### Principles
1. **Warm and human** — write as a friend, not a marketer
2. **Second person** — address the reader as "you" and "your"
3. **Evocative** — describe how the experience *feels*, not just what it includes
4. **Concise** — short sentences, strong verbs, no jargon
5. **Aspirational but accessible** — luxury tone without exclusivity

### Forbidden words
Never use in generated copy or UI strings:
- "embark", "journey", "unforgettable", "indulge", "luxurious"
- Corporate jargon: "leverage", "synergy", "world-class", "cutting-edge"

### Fixed UI strings

| Context | Correct copy |
|---------|-------------|
| Hero headline | "From data to stories. At scale." |
| CTA button | "Generate Content" |
| Empty/initial state | "Drop your CSV to begin" |
| Processing state | "Crafting your content..." |
| Success state | "Your content is ready" |

---

## Category tone guidelines

| Category | Tone |
|----------|------|
| `getaways` | Romantic and escapist — leaving the everyday behind |
| `wellness` | Calm, restorative, nurturing — genuine self-care |
| `adventure` | Energetic, exhilarating — bold experiences |
| `gastronomy` | Sensory, celebratory — pleasure of exceptional food |
| `pampering` | Indulgent, personal — being looked after |
