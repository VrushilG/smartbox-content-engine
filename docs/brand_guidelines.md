# Brand Guidelines — Smartbox Content Engine

## About Smartbox

Smartbox Group is Europe's leading experience gift company, headquartered in Dublin, Ireland. We sell moments — weekends away, spa days, adventure experiences, and culinary journeys — packaged as gift boxes. Our brand is warm, optimistic, and human.

**Brand platform:** *Choose Wisely* — one well-chosen experience can change everything. This is the Butterfly Effect of gifting: the right gift at the right moment doesn't just create a memory, it shifts someone's perspective.

---

## Design tokens

All tokens are defined as CSS custom properties in `frontend/src/css/main.css`. Never hardcode hex values anywhere else in the codebase.

### Colour palette

| Token | Value | Usage |
|-------|-------|-------|
| `--color-coral` | `#E8593C` | Primary CTA, progress fill, active borders, icons, prototype banner |
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

### Prototype disclaimer banner
- CSS class: `.prototype-banner`
- Background: `var(--color-coral)`
- Text colour: white
- Position: top of page — appears on both the auth overlay and the main app
- Text: *"This is a prototype built with open-source and paid tools, created exclusively for demonstration purposes as part of the interview process."*
- Font size: 0.8rem, weight 500
- Shown on every page load — not dismissible

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

| Word / phrase | Why forbidden |
|---------------|---------------|
| `embark` | Travel cliché |
| `journey` | Overused metaphor |
| `unforgettable` | Tells rather than shows |
| `indulge` | Sounds permission-seeking |
| `luxurious` | Exclusionary, vague |
| `amazing` | Meaningless filler |
| `incredible` | Meaningless filler |
| `perfect gift` | Generic, lazy |
| `treat yourself` | Overused, lacks warmth |
| `unique experience` | Every experience claims this |
| `leverage` | Corporate jargon |
| `synergy` | Corporate jargon |

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

The system prompt injects per-category tone guidance for every product row. The full creative direction for each category is defined in `backend/app/prompts/category_tones.py`.

### Getaways

**Tone:** Escapist, quietly romantic — the moment of leaving everyday life behind.

Write about open windows, fresh air, a new town, someone's hand on yours. Intimate and grounded joy — not grand declarations. The feeling of checking in somewhere and thinking *this is exactly what I needed*. Gentle, warmly evocative.

### Wellness

**Tone:** Calm, restorative, and gently humorous — the hard-won bliss of doing nothing.

Capture the almost absurd pleasure of being looked after — that half-asleep smile during a massage, the post-treatment glow, the silence you didn't know you needed. Avoid wellness clichés like "recharge" or "reconnect". Make it feel earned and real.

### Adventure

**Tone:** Energetic, daring, irreverently fun — celebrate the absurdity and the adrenaline.

Write with punchy rhythm. Capture the gritty joy of doing something hard or ridiculous — the laugh afterwards, the aching legs, the photo you couldn't not take. Accessible boldness, not extreme sport bravado. Short sentences. Strong verbs.

### Gastronomy

**Tone:** Sensory, warm, and celebratory — the ritual of exceptional food and drink.

Almost make them taste and smell it. The anticipation, the first bite, the clinking of glasses. Write about texture, temperature, the smell of something baking. Sophisticated but never snobbish — this is joy, not status.

### Pampering

**Tone:** Curious, infectious excitement — the nervousness before and the glow after.

Capture the specific, vivid *I can't believe I just did that* energy. Not generic relaxation — real reactions. The unexpected delight, the small luxuries that hit differently. Conversational and slightly surprised.

---

## Video template — branded box-opening sequence

Every generated video clip uses the same brand signature moment, defined in
`backend/app/prompts/video_template.py`:

```
Drone approaching Smartbox box in {environment_hint}. Box features Smartbox branding.
Lid opens with soft magical glow. Inside: {scene}.
Premium travel-commercial cinematic style, smooth camera motion,
natural lighting, joyful authentic emotions, 4 seconds total.
```

**How it works:**
- The LLM generates `{scene}` — a 15–25 word description of what the recipient experiences inside the box (e.g. *"a woman stepping into a mountain hot spring at dusk, face lighting up with joy"*)
- `{environment_hint}` is derived from the product's location (e.g. *"Irish countryside"*)
- The template wraps the scene with the Smartbox brand signature (drone approach → box opening → glow reveal) ensuring every video starts with a consistent branded moment
- No camera direction instructions in the `scene` — those are in the template

**Rules for `video_prompt` field generated by the LLM:**
- 15–25 words only
- Describe the scene *inside* the box: who, what, where, mood
- No camera movements, no "cinematic", no "4K" — the template handles all of that
- Grounded in the product's specific setting and key selling point

---

## DAM filename convention

All generated files follow this naming convention, constructed exclusively by `core/dam_naming.py`:

```
PROD-{product_id}_{CATEGORY}_{LOCALE}_{YYYYMMDD}.mp4
```

| Part | Source | Example |
|------|--------|---------|
| `PROD-` | Fixed prefix | `PROD-` |
| `{product_id}` | CSV `id` column | `1002` |
| `{CATEGORY}` | CSV `category` uppercased | `WELLNESS` |
| `{LOCALE}` | `DEFAULT_LOCALE` env var (default: `IE`) | `IE` |
| `{YYYYMMDD}` | UTC date of generation | `20260317` |

**Full example:** `PROD-1002_WELLNESS_IE_20260317.mp4`

Valid category values in filenames: `GETAWAYS`, `WELLNESS`, `ADVENTURE`, `GASTRONOMY`, `PAMPERING`

**Rule:** This string is never constructed outside of `core/dam_naming.py`. Do not build it inline anywhere else in the codebase.
