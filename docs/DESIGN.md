# Design system

The approved screens are the Bodha Coder design canvas. These rules bind every screen.

## Type

One family: the Apple system font (`-apple-system, BlinkMacSystemFont, "SF Pro Text"` and
`"SF Pro Display"` for titles), with Inter where SF is unavailable. No serif, no italic display
face, no separate code font: codes use the same family with tabular figures.

| Role | Size and weight |
|---|---|
| Large title | 34, bold, tracking -0.025em |
| Title | 20 to 24, semibold |
| Headline | 15 to 17, semibold |
| Body | 14, regular |
| Secondary | 12.5 to 13, regular, secondary label colour |

## Colour

| Token | Value | Use |
|---|---|---|
| page | #FAFAF8 | page background |
| surface | #FFFFFF | panels |
| sidebar | #F2F2F4 | navigation |
| separator | #E5E5EA | lines |
| label | #1D1D1F | text |
| secondary | #6E6E73 | secondary text |
| tertiary | #6E6E73 | the smallest labels; same colour as secondary so it passes 4.5:1 on the sidebar, set apart by size |
| action | #3A2470 (hover #2D1B59) | the primary action button only |
| ok | #34C759 | supported, matches |
| warn | #FF9F0A | needs detail |
| bad | #FF3B30 | not supported, billed too high |
| low | #0A84FF | billed too low |

Status is a small dot beside a word, never colour alone. Dark purple appears on the primary
action button and nowhere else.

## Shape and controls

Grouped panels with 14px radius, pill buttons (primary, secondary, plain, danger), segmented
controls, macOS-style sidebar with small line icons, toggles in system green. One primary action
per screen. No helper sentences: labels, layout and state carry the meaning.

## Feedback and flow

A reversible action (approve, approve all) happens at once and offers Undo in a toast at the bottom
for eight seconds; a confirmation dialog is kept for destructive actions only (delete, replace a PDF,
block). Loads that fill a screen show a skeleton of its layout; small panels keep the spinner. In
note review the finding that `y` and `n` act on carries a dark bar at its left edge, and focus moves
to the next finding after each decision, then to Approve. Form fields are checked when they lose
focus, not only on submit.

Text meets WCAG 2.2 AA contrast (4.5:1) on every surface, including the sidebar. Apple's lighter
tertiary grey (#86868B) reaches only 3.2:1 on the sidebar, so it is used for decoration such as focus
rings, never for text.

## Motion and haptics

Motion explains what Bodha does: a reading beam, evidence inked like a marker, a struck code replaced by
the supported one, pages that land, wires that connect a sentence to its code. It never decorates a
control. Rules:

| Rule | How |
|---|---|
| Cheap to draw | only `transform`, `opacity`, `background-size` and `stroke-dashoffset` animate; no animation libraries |
| Scroll without React | `ScrollStage` writes one `--p` (0 to 1) per section in a `requestAnimationFrame`; CSS derives every act from it |
| Paused off screen | `MotionRoot` marks `[data-live]` elements with `data-onscreen`; infinite animations pause when false |
| Reveals | elements with `data-reveal` below the fold wait (`data-state="waiting"`) and ease in once seen; without JavaScript everything is visible |
| Reduced motion | `prefers-reduced-motion: reduce` shows every final state, unpins the story and lays its acts out as rows |
| Pointer | parallax and the magnetic button follow fine pointers only |
| Haptics | `lib/haptics.ts`: `tap` (primary press), `select` (switch, in-page jump), `success` (approve). The Vibration API where it exists (Android); on touch devices without it, a hidden native switch is ticked, which iOS 18 answers with a system haptic. Only from a user gesture, never on scroll |

