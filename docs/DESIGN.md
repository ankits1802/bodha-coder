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
