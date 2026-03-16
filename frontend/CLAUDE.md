# Frontend — Smartbox Content Engine

## Stack
- Vanilla HTML + CSS + JavaScript (ES modules)
- NO build step, NO npm, NO bundler
- Inter font from Google Fonts CDN
- Served as static files by FastAPI from frontend/src/

## Smartbox brand — STRICTLY FOLLOW
This app will be demoed to the Smartbox CMO and Head of Content Automation.
Every design decision must reflect the Smartbox brand.

### Color tokens (defined in css/main.css — never hardcode hex values in HTML or JS)
--color-coral: #E8593C
--color-coral-hover: #D14A2E
--color-coral-tint: #FFF0EC
--color-navy: #1A1A2E
--color-dark-surface: #2D2D44
--color-warm-white: #F9F6F2
--color-text-primary: #1A1A2E
--color-text-muted: #6B6B80

### Typography
Font: Inter (400, 500, 600 weights only)
Headings: 500 weight
Body: 400 weight, 16px, line-height 1.6

### Component rules
- Cards: border-radius 12px, background var(--color-dark-surface) on dark sections
- CTA button: coral background, white text, border-radius 8px, no border
- Category pills: coral-tint background, coral text, border-radius 20px
- DAM filename: monospace font, muted color, badge style
- Progress bar fill: var(--color-coral)
- Drag-drop zone: dashed 2px coral border, coral-tint background on hover

### Brand voice in all UI copy
- Warm, human, second-person — never technical or robotic
- Hero line: "From data to stories. At scale."
- CTA label: "Generate Content"
- Empty state: "Drop your CSV to begin"
- Processing label: "Crafting your content..."
- Success label: "Your content is ready"

## File responsibilities
- index.html      — shell, meta tags, font imports, mounts #app div
- js/app.js       — initialises all modules, wires events
- js/api.js       — fetch wrapper and SSE EventSource client
- js/ui.js        — renders result cards, progress bars, status updates
- js/uploader.js  — drag-drop CSV handler, file validation
- css/main.css    — design tokens, base reset, layout, typography
- css/components.css — cards, buttons, pills, progress, upload zone

## Rules
- NEVER inline styles in HTML — all styling via CSS classes
- All CSS custom properties must be defined in main.css first
- SSE events from backend drive all UI state — never poll
- NEVER hardcode any hex color values outside of main.css
