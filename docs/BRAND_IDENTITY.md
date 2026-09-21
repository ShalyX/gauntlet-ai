# GauntletAI — Brand Identity & Design Token Specification

**Version**: 1.0 (Production Launch)  
**Target Domain**: On-Chain AI Agent Security & Financial Settlement  
**Design Philosophy**: Institutional Banking & High-Density Developer Platform (*"Deep navy ledger under cool dawn"*)

---

## 1. Concept & Symbolism: The Invariant Aperture

The GauntletAI identity rejects the generic iconography of both Web3 (floating neon cubes, glowing coins, arbitrary node meshes) and AI devtools (sparkles, floating brains, robot heads with glowing eyes).

Instead, the mark derives directly from the product's actual mechanism: **adversarial containment and multi-validator inspection**.

```
       ▲  [Multi-Validator Probes]
       │
   ┌───┴───┐
   │ ┌───┐ │
   │ │ G │ │  <── The Invariant Aperture (Interlocking "G" Monolith)
   │ └───┘ │      Central Canary Chamber Under Adversarial Stress
   └───────┘
```

### The Visual Mechanism
1. **The Outer Monolith**: A heavy, precision-engineered geometric contour with high optical weight that forms an unmistakable uppercase **`G`**.
2. **The Central Aperture**: A calibrated square core (`#0e8a72`) positioned within the negative space, representing the agent's execution boundary under multi-validator inspection.
3. **Small-Size Resilience**: The mark retains complete structural recognition at 16×16px (browser tab favicon) while scaling to large-format conference banners.

---

## 2. Cliché Rejection & Ownability Audit

| Category Cliché | Why It Was Rejected | GauntletAI Ownable Solution |
| :--- | :--- | :--- |
| **Padlocks & Shields** | Overused by generic VPNs and antivirus software; communicates passive perimeter defense rather than active adversarial testing. | **Monolithic Geometric "G"**: Communicates an active proving ground and institutional settlement gate. |
| **Robot Heads & Brains** | AI marketing fluff; communicates consumer chatbots rather than high-stakes on-chain treasury custody. | **Calibrated Invariant Aperture**: Highlights precision testing of software invariants. |
| **Neon Purple/Cyan Glow** | Generic hackathon aesthetic; destroys contrast and readability in high-density data tables. | **Restrained Palette**: Column Navy (`#111a4a`) paired with Seafoam (`#0e8a72`) and Cloud Canvas (`#f6f6f8`). |
| **Emojis as UI Icons** | Diminishes trust and credibility in financial protocols. | **Strict Vector SVGs**: Dedicated vector icons with consistent optical stroke weight. |

---

## 3. Official Color System & Design Tokens

```
Column Navy        Deep Slate         Seafoam 700        Seafoam 500        Signal Crimson     Cloud Canvas       Hairline Border
#111a4a            #0e153a            #0e8a72            #44b48b            #c0263f            #f6f6f8            #e3e4e8
[Primary Brand]    [Dark Surfaces]    [Verified Metric]  [Active Accent]    [Slash & Alert]    [Canvas Base]      [Dividers]
```

### Color Token Table

| Token Name | HEX | RGB | Semantic Role |
| :--- | :--- | :--- | :--- |
| `--color-navy-primary` | `#111a4a` | `rgb(17, 26, 74)` | Primary brand color, headers, primary buttons, authoritative typography |
| `--color-navy-dark` | `#0e153a` | `rgb(14, 21, 58)` | Deep backgrounds, terminal containers, header background |
| `--color-seafoam-700` | `#0e8a72` | `rgb(14, 138, 114)` | Verified defense scores, active licenses, success badges |
| `--color-seafoam-500` | `#44b48b` | `rgb(68, 180, 139)` | Interactive accents, hover states on dark surfaces |
| `--color-crimson-alert`| `#c0263f` | `rgb(192, 38, 63)` | Slashing events, breach warnings, dispute triggers |
| `--color-canvas-cloud` | `#f6f6f8` | `rgb(246, 246, 248)`| Page canvas background, input backgrounds, subtle card surfaces |
| `--color-canvas-white` | `#ffffff` | `rgb(255, 255, 255)`| Raised cards, modals, table surfaces |
| `--color-border-hairline`| `#e3e4e8` | `rgb(227, 228, 232)`| Hairline borders for cards, tables, and dividers |
| `--color-slate-subtle` | `#4a5568` | `rgb(74, 85, 104)` | Secondary body copy, table labels, descriptive annotations |

---

## 4. Typography Hierarchy

| Role | Typeface | Weights | Letterspacing | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **Display Headings** | `Inter` | Bold (700), Extra Bold (800) | `-0.035em` to `-0.04em` | Page titles, hero headlines, modal titles |
| **Section & UI Labels** | `Inter` | Medium (500), SemiBold (600) | `-0.01em` | Table column headers, button labels, navigation tabs |
| **Body Copy** | `Inter` | Regular (400) | `0em` | Explanatory copy, documentation text, tooltips |
| **Data & Hashes** | `JetBrains Mono` | Medium (500), SemiBold (600) | `0em` to `+0.04em` | Contract addresses, transaction hashes, BPS scores, GEN stakes |
| **Protocol Badges** | `JetBrains Mono` | Bold (700) | `+0.08em` | `PROTOCOL`, `STUDIONET 61999`, `SEV-1 CRITICAL` |

---

## 5. Vector Asset Inventory

All brand assets are authored as clean, standalone vector SVGs with zero external raster dependencies:

| Asset | Location | Dimensions | Purpose |
| :--- | :--- | :--- | :--- |
| **Logo Mark** | `frontend/assets/brand/logo-mark.svg` | `128×128` | Standalone icon for avatar, nav brand glyph, and app icons |
| **Logo Lockup** | `frontend/assets/brand/logo-lockup.svg` | `320×64` | Horizontal brand lockup (`[G] GauntletAI PROTOCOL`) |
| **Browser Favicon** | `frontend/assets/brand/favicon.svg` | `32×32` | High-contrast favicon for browser tabs and bookmarks |
| **Open Graph Card** | `frontend/assets/brand/og-image.svg` | `1200×630` | Social card for Twitter/X, Discord, Telegram, and GitHub unfurls |
| **README Hero** | `docs/assets/readme-hero.svg` | `1280×420` | Widescreen hero banner for GitHub and documentation portals |

---

## 6. Usage Guidelines

### Do's
* Maintain the high-contrast relationship between Column Navy (`#111a4a`) and Seafoam (`#0e8a72`).
* Use `JetBrains Mono` exclusively for hashes, numbers, and technical tags.
* Ensure cards have solid white or cloud backgrounds with hairline borders (`#e3e4e8`).

### Don'ts
* Never use neon purple, cyan, or magenta glow blobs.
* Never use emojis (🚀, 💡, ⚡, 🛡️, 🤖) as UI graphics or navigation icons.
* Never stretch or distort the geometric proportions of the Invariant Aperture mark.
