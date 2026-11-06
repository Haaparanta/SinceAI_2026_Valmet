# ⚡ Cyberpunk Theme v2

`// DESIGN SYSTEM` · `v2.0.0 · UPDATED 2026-11-06 · STATUS: ONLINE`

The visual language for everything this team ships: the plant-twin web app, the briefing card, the deck and the docs. **Professional first, fun second.** It has Apple-level precision and restraint, shadcn/ui structure, and a neon-on-midnight personality.

- **Feels like:** a night city seen through a car window, a premium terminal, a pro-grade instrument panel.
- **Reads like:** a serious, high-performance industrial product. The neon guides the eye; it doesn't scream.
- **Rule of thumb:** 85% dark calm, 15% neon signal.

**Source of truth for values:** [`cyberpunk-tokens.css`](cyberpunk-tokens.css). This guide explains how to use them.

### What changed from v1

| Area | v1 | v2 |
|---|---|---|
| Semantic colors | Yellow/green named in prose but had no tokens | `--warning`, `--success` (+ foregrounds) in both modes |
| Daylight mode | No chart, sidebar, glow or grid tokens | Complete token set, with glows tuned down for light surfaces |
| Domain fit | Generic | **Plant-twin tokens:** `--status-ok/watch/alert/unknown`, `--route`, `--selection`, `--scene-bg`, `--scene-points` |
| Glow names | `--glow-cyan`, `--glow-magenta` | Role-based `--glow-primary`, `--glow-accent` (old names kept as aliases) |
| Motion | Described in prose | `--ease-snap`, `--dur-fast`, `--dur-base` tokens and a global reduced-motion guard |
| Contrast | Daylight muted text was borderline | Daylight `--muted-foreground` and `--primary` darkened for WCAG AA on `--background` |
| Accessibility | Color carried status | **Status is never color-only.** Always pair it with a label or icon (see §6) |
| Tailwind | Not covered | Tailwind v4 `@theme inline` mapping (§9) |

---

## 1. Principles (Apple HIG, jacked in)

| Principle | What it means here |
|---|---|
| **Clarity** | Neon is for signal, not for paragraphs. Body text is soft off-white. Contrast ≥ WCAG AA. |
| **Deference** | Dark, quiet surfaces let content glow. Chrome recedes into shadow. The **3D scene** is the hero; the UI frames it. |
| **Depth** | Translucent dark glass, inner borders and colored glow, not drop shadows. |
| **Consistency** | Every value comes from a token. Neon has fixed meaning (§2). |
| **Delight** | Micro-moments only: one scanline on load, a glow on focus, a terminal cursor in empty states. |

## 2. Semantic neon (never swap meanings)

| Token | Night City | Meaning | Plant-twin use |
|---|---|---|---|
| `--primary` | neon cyan | Action, focus, navigation | Buttons, focus rings, **route line** |
| `--accent` | hot magenta | Highlight, new, selected | **Selected asset**, "recommended" badges |
| `--warning` | acid yellow | Caution | **Equipment status: WATCH** |
| `--success` | matrix green | OK, done | **Equipment status: OK**, answered/saved |
| `--destructive` | alarm red | Error, danger | **Equipment status: ALERT**, destructive actions |
| `--muted-foreground` | cool grey | Unknown, secondary | **Equipment status: UNKNOWN** |

Use **at most two neon colors in one component.** The 3D scene counts as one component, so the selection color (magenta) has to stay distinct from the status colors.

## 3. Typography

```css
--font-sans:    -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", system-ui, sans-serif;
--font-display: "SF Pro Display", "Space Grotesk", var(--font-sans);
--font-mono:    "SF Mono", "JetBrains Mono", "Berkeley Mono", ui-monospace, Menlo, monospace;
```

| Role | Size / LH | Weight | Font |
|---|---|---|---|
| Large Title | 34 / 41 | 700 | Display, `tracking-tight` |
| Title 1 | 28 / 34 | 700 | Display |
| Title 2 | 22 / 28 | 600 | Display |
| Eyebrow / Label | 11 / 14 | 600 | **Mono, UPPERCASE, `tracking-[0.2em]`**, primary |
| Headline | 17 / 22 | 600 | Sans |
| Body | 17 / 24 (16 / 24 on mobile) | 400 | Sans |
| Data / Numbers | 15 / 20 | 500 | Mono, `tabular-nums` |
| Caption | 12 / 16 | 500 | Mono, muted |

- Eyebrows above headings: `// SYSTEM STATUS`, `[ 01 ] OVERVIEW`.
- Numbers, IDs (`P-101`, `WO-2231`), timestamps, units (`48 m`) and versions are always mono.
- Body text stays sans. Never set paragraphs in uppercase or in neon.
- SF fonts aren't loaded from the web, because of their license. On non-Apple devices the stack falls back to Inter, JetBrains Mono or the system fonts.

## 4. Layout, spacing & shape

- **Grid:** 8pt base. Dense where data lives, spacious where reading happens.
- **Max width:** 720px for documents, 1280px for dashboards. The 3D view may go full-bleed.
- **Mobile:** 16px side gutter, no horizontal scroll, tap targets ≥ 44px.
- **Radius:** cards `rounded-xl`, buttons `rounded-lg`, inputs `rounded-md`, badges `rounded-sm`. Optional clipped corner on hero cards: `clip-path: polygon(0 0, calc(100% - 16px) 0, 100% 16px, 100% 100%, 0 100%)`.
- **Depth:** 1px inner borders (`--border`). Glow (`--glow-primary`) only for focus, hover and active states.
- **Canvas:** optional `--grid-bg` (`background-size: 32px 32px`) on the page canvas, never directly behind text. Cards sit on top of it with an opaque or glass fill.
- **Motion:** `var(--ease-snap)`, 150–250ms. At most one scanline or flicker, on mount. Respect `prefers-reduced-motion` (the token file already does this globally).

## 5. shadcn/ui components

| Component | Treatment |
|---|---|
| `Button` default | Cyan fill, dark text, `hover:shadow-[var(--glow-primary)]` |
| `Button` outline | Transparent, 1px cyan border, cyan text, glow on hover |
| `Button` secondary | Gunmetal fill, soft white text |
| `Button` destructive | Red outline by default. Fill red only in the confirm step |
| `Card` | `bg-card/80 backdrop-blur`, 1px cyan-tinted border, optional corner brackets |
| `Badge` | `rounded-sm`, mono uppercase 11px, tinted fill (`bg-primary/15 text-primary`) |
| `Input` / `Textarea` | Dark fill, `rounded-md`, cyan ring + glow on focus, mono placeholder `> enter value_` |
| `Switch` | Cyan with glow when on; flat thumb |
| `Tabs` | Underline style, active tab has a 2px cyan bar + glow |
| `Dialog` / `Sheet` | Dark glass, cyan top border, eyebrow in the header |
| `Sonner` | Mono text, colored left bar by status, `[OK]` / `[ERR]` / `[WARN]` prefixes |
| `Sidebar` | Near-black glass, active item = cyan left bar + `bg-sidebar-accent` |
| `Table` | Mono numbers, row hover `bg-primary/5`, sticky eyebrow-style header |
| `Chart` | `--chart-1…5`, thin lines with subtle glow, faint grid |
| `Progress` | Thin track (`--muted`), cyan fill, mono `07/10` counter beside it |

## 6. Plant-twin specifics (new in v2)

- **3D scene:** background `--scene-bg`, points `--scene-points` at a low size. The scene stays quiet so the overlays read clearly.
- **Equipment boxes:** wireframe in the status color at 1px, plus a 10% fill tint of the same color. Show labels on hover or selection only (mono, e.g. `P-101 · PUMP · ALERT`).
- **Selected asset:** `--selection` wireframe at 2px plus `--glow-accent`. Selection always overrides the status color for the outline, and the status stays visible in the label badge.
- **Route:** `--route` polyline, 3px, with a soft glow. Animate it drawing once (≤ 600ms), then keep it static.
- **Status is never color-only:** every status chip carries text (`OK` / `WATCH` / `ALERT` / `UNKNOWN`). Colorblind users and grayscale print must still work.
- **Synthetic data:** show a persistent `SYNTHETIC DATA` badge (warning tint) whenever `Scene.is_synthetic` is true.
- **Demo Mode:** show a `DEMO MODE · CACHED` badge (accent tint) in the status bar while it is on.

## 7. Documents (README, reports, pm_pack)

GitHub markdown can't load CSS, so documents carry the theme through **structure**:

- **Title block:** an eyebrow in inline code (`` `// PROJECT` ``), then H1, a muted one-line subtitle, and a mono metadata row (`` `v2.1.0 · UPDATED 2026-11-06 · STATUS: ONLINE` ``).
- **Callouts:** use GitHub alerts, which render with colored bars:
  - `> [!NOTE]` for info (cyan role)
  - `> [!TIP]` for highlight (magenta role)
  - `> [!WARNING]` for warn (yellow role), e.g. the "provisional" notices
  - `> [!CAUTION]` for critical (red role)
- **Tables:** short uppercase headers, IDs and numbers in inline code.
- **Dividers:** `---`, or a mono section marker: `` `── [ 02 ] ──` ``.
- **Images and diagrams:** dark frame with corner brackets `⌜ ⌝ ⌞ ⌟`.
- **HTML exports** (decks, reports): use `cyberpunk-tokens.css` directly. Daylight is preferred for print.

## 8. Voice & microcopy

Precise, cool and quietly witty, like a capable netrunner who writes clean docs.

| Instead of | Say |
|---|---|
| "Operation successful" | "`[OK]` Changes synced." |
| "No items found" | "No signal yet. Create your first entry_" |
| "Loading…" | "Establishing uplink…" |
| "Error: invalid input" | "`[ERR]` That email format didn't parse." |
| "Processing point cloud…" | "Mapping the plant… `1.2M pts`" |
| "No route found" | "`[ERR]` No walkable path to `P-101`. Check blocked areas." |
| "Submit" | "Save changes" (CTAs stay plain; flavor goes in the surrounding copy) |

**No flavor text** in errors that need action, in safety or maintenance instructions, or in legal and security flows. Maintenance advice is always plain language.

## 9. Tailwind v4 + shadcn/ui wiring

```css
/* app.css */
@import "tailwindcss";
@import "../../design/cyberpunk-tokens.css";
@custom-variant dark (&:is(.dark *));

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-popover: var(--popover);
  --color-popover-foreground: var(--popover-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-destructive: var(--destructive);
  --color-warning: var(--warning);
  --color-warning-foreground: var(--warning-foreground);
  --color-success: var(--success);
  --color-success-foreground: var(--success-foreground);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);
  --color-chart-1: var(--chart-1);
  --color-chart-2: var(--chart-2);
  --color-chart-3: var(--chart-3);
  --color-chart-4: var(--chart-4);
  --color-chart-5: var(--chart-5);
  --color-sidebar: var(--sidebar);
  --color-sidebar-foreground: var(--sidebar-foreground);
  --color-sidebar-primary: var(--sidebar-primary);
  --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
  --color-sidebar-accent: var(--sidebar-accent);
  --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
  --color-sidebar-border: var(--sidebar-border);
  --color-sidebar-ring: var(--sidebar-ring);
  --font-sans: var(--font-sans);
  --font-mono: var(--font-mono);
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) + 4px);
}
```

Set `<html class="dark">` by default. A theme toggle only removes the class, and the choice is stored per viewer.

## 10. Do & don't

✅ **Do**
- Default to dark, and keep neon scarce and meaningful.
- Use mono for data, labels and metadata.
- Use glow only for focus, hover, active and the selected asset.
- Pair every status color with a text label.

❌ **Don't**
- Set paragraphs in neon or all-caps.
- Use constant flicker, glitch effects on text, or more than two neon colors in one component.
- Use pure `#000` or `#fff` on large areas.
- Hard-code a hex or OKLCH value outside `cyberpunk-tokens.css`.

## 11. Ship checklist

- [ ] All colors come from `cyberpunk-tokens.css` (Night City + Daylight)
- [ ] Text contrast passes WCAG AA; neon text appears only on dark surfaces
- [ ] Spacing follows the 8pt grid; mobile has a 16px gutter and no horizontal scroll
- [ ] Components are shadcn/ui primitives with theme classes, not one-offs
- [ ] Status is never conveyed by color alone
- [ ] `prefers-reduced-motion` is respected
- [ ] Neon and flavor elements are ≤ 15% of the visual weight
