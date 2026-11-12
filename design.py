"""Pond, the Sliced Bread design system: tokens, the Gradio theme, the CSS and the mallard. See PLAN.md section 5.

Green marks what you can press; red means over budget. Meters fill in plain ink, and their words say near or over.
Nothing in app.py sets a colour or size by hand.
"""

import html
import math

import gradio as gr

import budget

# ---------- Tokens ----------

PAPER = "#F4F2ED"  # page background, a shade darker than cards so they stand off it
PAPER_DEEP = "#E9E5DD"  # the tab switcher's track
CARD = "#FFFFFF"  # cards
INK = "#1C1B18"  # all text, all money
MUTED = "#6B665D"  # labels, 5:1 on paper
LINE = "#E2DDD3"  # card borders, dividers, empty meter track
FIELD_BORDER = "#958D81"  # text box borders, 3.3:1 on white so a box reads as a box
ACCENT = "#1F7A4D"  # mallard green: buttons, focus; white text on it is 5.3:1
ACCENT_DARK = "#17603C"  # button hover
ACCENT_SOFT = "#E7F1EA"  # add/edit panel, avatar
HOVER = "#F0EDE7"  # neutral hover for quiet icon buttons
OVER = "#B42318"  # "Over budget" text

# Fills only (dots, donut, chart columns), never text. Every colour also carries its name (marker, key, legend).
INCOME_COLOR = "#F2C230"  # yellow
CATEGORY_COLORS = {
    "needs": "#8A8F98",  # grey: Necessities
    "wants": "#FB4F14",  # Bengals orange: Discretionary
    "investing": "#A070F0",  # purple
    "savings": "#E0559F",  # pink
}
SAVINGS_SOFT = "#FCEAF3"  # the Savings card's wash, a tint of its colour
SAVINGS_EDGE = "#F5C6DE"  # its border
# A category's subcategories run from a little darker than its colour to a little lighter, so the dot says the category.
SUBCATEGORY_DARKEST_MIX = 0.2  # share of black in the first subcategory's shade (when there is more than one)
SUBCATEGORY_LIGHTEST_MIX = 0.35  # share of white in the last
# History zoom: a category's lines run from its colour mixed toward black (biggest) to toward white (smallest).
DARKEST_MIX = 0.35  # share of black in the biggest line's shade
LIGHTEST_MIX = 0.6  # share of white in the smallest; any lighter fades into the white card
ITEM_LIGHTEST_MIX = 0.4  # same, from a subcategory's colour, which may already be up to 35% white

# The mallard's own colours. Duck only; never used for UI.
DUCK_HEAD = "#1D6B47"
DUCK_BILL = "#E8B931"
DUCK_BREAST = "#7A3E1D"
DUCK_BODY = "#B9B3A8"

# The hero donut, in px.
DONUT_SIZE = 220
DONUT_STROKE = 24  # ring thickness: thin for its size, so the number in the middle leads
DONUT_GAP = 2  # card-coloured gap between segments

FONT_TEXT = "Geist"
FONT_DISPLAY = "Instrument Serif"
PAGE_MAX_WIDTH = "640px"

# ---------- Scripts the page runs ----------

# Amount boxes (class sb-money-input) show "$1,234.56" as you type. The caret keeps its place among the digits, and
# a fresh input event tells Gradio the new text; formatting twice changes nothing, so that event stops there.
MONEY_INPUT_SCRIPT = r"""<script>
function sbMoneyText(text) {
  var cleaned = text.replace(/[^0-9.]/g, '');
  if (!cleaned) return '';
  var point = cleaned.indexOf('.');
  var whole = (point < 0 ? cleaned : cleaned.slice(0, point)).replace(/^0+(?=\d)/, '');
  var fraction = point < 0 ? null : cleaned.slice(point + 1).replace(/\./g, '').slice(0, 2);
  whole = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',') || (fraction !== null ? '0' : '');
  return '$' + whole + (fraction !== null ? '.' + fraction : '');
}
document.addEventListener('input', function (event) {
  var box = event.target;
  if (!box.closest || !box.closest('.sb-money-input')) return;
  var typed = box.value, formatted = sbMoneyText(typed);
  if (formatted === typed) return;
  var after = typed.slice(box.selectionEnd || typed.length).replace(/[^0-9.]/g, '').length;
  var caret = formatted.length, seen = 0;
  while (caret > 0 && seen < after) { caret--; if (/[0-9.]/.test(formatted[caret])) seen++; }
  box.value = formatted;
  box.setSelectionRange(caret, caret);
  box.dispatchEvent(new Event('input', {bubbles: true}));
});
</script>"""

# Loaded in <head> so both faces are ready before first paint.
HEAD = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&'
    'family=Instrument+Serif:ital@0;1&display=swap">'
    # History: clicking anything with data-sb-zoom picks that category in the hidden radio, which redraws the chart.
    "<script>document.addEventListener('click', function (event) {"
    "  var target = event.target.closest && event.target.closest('[data-sb-zoom]');"
    "  if (!target) return;"
    "  var choice = target.getAttribute('data-sb-zoom');"
    "  document.querySelectorAll('.sb-category-pick label').forEach(function (label) {"
    "    if (label.textContent.trim() === choice) label.querySelector('input').click();"
    "  });"
    "});</script>"
    + MONEY_INPUT_SCRIPT
)

# ---------- The Gradio theme ----------

# Green and paper as Gradio colour ramps, so built-in components pick them up.
ACCENT_RAMP = gr.themes.Color(
    c50="#F2F8F4", c100=ACCENT_SOFT, c200="#C5DFCF", c300="#94C4A6", c400="#5BA37A", c500="#2F8A5B",
    c600=ACCENT, c700=ACCENT_DARK, c800="#124A2F", c900="#0D3622", c950="#082416", name="accent",
)
PAPER_RAMP = gr.themes.Color(
    c50=PAPER, c100=PAPER_DEEP, c200=LINE, c300="#C9C1B4", c400=FIELD_BORDER, c500="#7D776D",
    c600=MUTED, c700="#4A4640", c800="#2F2C28", c900=INK, c950="#141311", name="paper",
)


def build_theme():
    """The Gradio theme. Light only: every dark-mode value is copied from its light twin."""
    theme = gr.themes.Base(
        primary_hue=ACCENT_RAMP,
        secondary_hue=ACCENT_RAMP,
        neutral_hue=PAPER_RAMP,
        font=[FONT_TEXT, "ui-sans-serif", "system-ui", "sans-serif"],
        font_mono=["ui-monospace", "Consolas", "monospace"],
        text_size=gr.themes.sizes.text_md,
    ).set(
        body_background_fill=PAPER,
        body_text_color=INK,
        body_text_color_subdued=MUTED,
        background_fill_primary=CARD,
        background_fill_secondary=PAPER,
        border_color_primary=LINE,
        border_color_accent=LINE,
        color_accent=ACCENT,
        color_accent_soft=ACCENT_SOFT,
        block_background_fill=CARD,
        block_border_color=LINE,
        block_border_width="0px",
        block_shadow="none",
        block_padding="0px",
        block_title_text_color=MUTED,
        block_title_text_size="14px",
        block_title_text_weight="500",
        block_label_text_color=MUTED,
        input_background_fill=CARD,
        input_border_width="1px",
        input_border_color=FIELD_BORDER,
        input_border_color_hover=INK,
        input_border_color_focus=ACCENT,
        input_shadow="none",
        input_shadow_focus="none",
        input_radius="12px",
        input_padding="12px 14px",
        input_text_size="16px",
        button_large_radius="999px",
        button_small_radius="999px",
        button_large_padding="12px 22px",
        button_large_text_size="16px",
        button_large_text_weight="600",
        button_border_width="1px",
        **{f"button_{kind}_shadow{state}": "none" for kind in ("primary", "secondary", "cancel") for state in ("", "_hover", "_active")},
        layout_gap="16px",
        button_primary_background_fill=ACCENT,
        button_primary_background_fill_hover=ACCENT_DARK,
        button_primary_text_color="#FFFFFF",
        button_primary_border_color=ACCENT,
        button_primary_border_color_hover=ACCENT_DARK,
        button_secondary_background_fill=CARD,
        button_secondary_background_fill_hover=HOVER,
        button_secondary_text_color=INK,
        button_secondary_border_color=LINE,
        button_secondary_border_color_hover=FIELD_BORDER,
        button_cancel_background_fill=CARD,
        button_cancel_background_fill_hover="#FBEDEB",
        button_cancel_text_color=OVER,
        button_cancel_border_color="#E8B4AE",
    )
    for name in list(vars(theme)):
        if name.endswith("_dark"):
            setattr(theme, name, getattr(theme, name.removesuffix("_dark")))
    return theme


# ---------- The CSS ----------

CSS = f"""
:root {{
  --sb-paper: {PAPER}; --sb-paper-deep: {PAPER_DEEP}; --sb-card: {CARD}; --sb-ink: {INK}; --sb-muted: {MUTED};
  --sb-line: {LINE}; --sb-accent: {ACCENT}; --sb-accent-dark: {ACCENT_DARK}; --sb-accent-soft: {ACCENT_SOFT};
  --sb-hover: {HOVER}; --sb-over: {OVER};
  --sb-serif: '{FONT_DISPLAY}', Georgia, 'Times New Roman', serif;
  --sb-sans: '{FONT_TEXT}', ui-sans-serif, system-ui, sans-serif;
}}

/* One centred column, phone first. */
.gradio-container {{
  width: 100% !important; max-width: {PAGE_MAX_WIDTH} !important; margin: 0 auto !important; padding: 20px 16px 48px !important;
  font-family: var(--sb-sans) !important; -webkit-font-smoothing: antialiased;
}}
.gradio-container .main {{ padding: 0 !important; }}
.gradio-container .main > .wrap > .contain > .column {{ gap: 16px !important; }}
footer {{ display: none !important; }}

/* No backlights: Gradio's busy fade, accent border and progress overlay are off; keyboard focus keeps a thin ring. */
.pending {{ opacity: 1 !important; animation: none !important; }}
.block.border_focus, .block.border_contrast {{ border-color: transparent !important; }}
.wrap.default, .wrap.center, .wrap.translucent, .eta-bar, .progress-level, .progress-text, .meta-text {{ display: none !important; }}
:focus {{ outline: none; }}
:focus-visible {{ outline: 2px solid var(--sb-accent) !important; outline-offset: 2px; box-shadow: none !important; }}
textarea:focus-visible, input:focus-visible {{ outline: none !important; }}

/* Type: 14 / 16 / 20 / 26 / 40 / 64. Serif for display, Geist for everything else. Nothing under 14. */
.sb-serif, .sb-wordmark, .sb-title, .sb-hero-amount, .sb-big {{
  font-family: var(--sb-serif); font-weight: 400; letter-spacing: -0.01em;
}}
.sb-wordmark {{ font-size: 26px; line-height: 1; }}
.sb-title {{ font-size: 26px; line-height: 1.1; display: flex; align-items: center; gap: 10px; }}
.sb-eyebrow {{ font-size: 14px; font-weight: 500; color: var(--sb-muted); }}
.sb-note {{ font-size: 14px; color: var(--sb-muted); line-height: 1.45; }}
.sb-money {{ font-variant-numeric: tabular-nums; white-space: nowrap; font-weight: 500; }}
.sb-hero-amount {{ font-size: 64px; line-height: 1; margin-top: 6px; font-variant-numeric: tabular-nums; }}
.sb-hero-amount.sb-over {{ color: var(--sb-over); }}
.sb-big {{ font-size: 40px; line-height: 1; font-variant-numeric: tabular-nums; }}
@media (max-width: 480px) {{
  .sb-hero-amount {{ font-size: 48px; }}
  .sb-title {{ font-size: 24px; }}
}}
.sb-dot {{ width: 10px; height: 10px; border-radius: 999px; display: inline-block; flex: none; }}
.sb-marker {{
  display: inline-flex; align-items: center; gap: 6px; padding: 2px 10px 2px 8px; border-radius: 999px; flex: none;
  border: 1px solid var(--sb-line); background: var(--sb-card); font-family: var(--sb-sans); font-size: 14px;
  font-weight: 500; line-height: 1.4; color: var(--sb-muted); letter-spacing: 0; white-space: nowrap;
}}
.sb-marker .sb-dot {{ width: 8px; height: 8px; }}
.html-container, .prose {{ padding: 0 !important; }}

/* Cards: white on paper, 20px corners, one soft shadow. */
.sb-card {{
  background: var(--sb-card) !important; border: 1px solid var(--sb-line) !important; border-radius: 20px !important;
  padding: 20px !important; gap: 14px !important; box-shadow: 0 1px 2px rgb(28 27 24 / 0.04), 0 4px 16px rgb(28 27 24 / 0.04);
}}
@media (min-width: 600px) {{ .sb-card {{ padding: 24px !important; }} }}
.sb-card-savings {{ background: {SAVINGS_SOFT} !important; border-color: {SAVINGS_EDGE} !important; }}
.sb-row {{ align-items: center !important; gap: 8px !important; flex-wrap: nowrap !important; }}
.sb-grow {{ flex: 1 1 auto !important; min-width: 0 !important; }}
.sb-head {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
.sb-head-total {{ display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }}
.sb-head .sb-money {{ font-size: 16px; }}
.sb-chip {{
  display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 999px;
  background: var(--sb-accent-soft); color: var(--sb-accent-dark); font-size: 14px; font-weight: 500;
}}

/* Header: logo and wordmark left; the person's name and an avatar button right, which opens a small menu. */
.sb-app {{ position: relative; }}
.sb-header {{ align-items: center !important; flex-wrap: nowrap !important; gap: 10px !important; padding: 4px 4px 0; }}
.sb-brand {{ display: flex; align-items: center; gap: 10px; }}
.sb-person {{ flex: none !important; width: auto !important; }}
.sb-person-name {{ font-size: 14px; font-weight: 500; white-space: nowrap; }}
@media (max-width: 400px) {{ .sb-person-name {{ display: none; }} }}
.sb-avatar-button {{
  width: 40px !important; height: 40px; min-width: 40px !important; max-width: 40px; padding: 0 !important; flex: none !important;
  border: none !important; border-radius: 999px !important; background: var(--sb-accent-soft) !important;
  color: var(--sb-accent-dark) !important; font-weight: 600 !important; font-size: 16px !important;
}}
.sb-avatar-button:hover {{ background: #D5E8DC !important; }}
.sb-menu {{
  position: absolute !important; top: 52px; right: 0; z-index: 20; width: 200px !important; min-width: 0 !important;
  padding: 8px !important; gap: 2px !important; box-shadow: 0 8px 24px rgb(28 27 24 / 0.14) !important;
}}
.sb-menu-item {{
  justify-content: flex-start !important; border: none !important; background: transparent !important; box-shadow: none !important;
  border-radius: 10px !important; padding: 10px 12px !important; font-size: 15px !important; font-weight: 500 !important;
}}
.sb-menu-item:hover {{ background: var(--sb-hover) !important; }}
.sb-back-button {{
  align-self: flex-start; width: auto !important; min-width: 0 !important; flex: none !important; padding: 8px 4px !important;
  border: none !important; background: transparent !important; box-shadow: none !important;
  color: var(--sb-accent-dark) !important; font-size: 15px !important; font-weight: 600 !important;
}}

/* Subcategories: a group per category under its marker; each row renames, moves or removes one. */
.sb-group-head {{ margin-top: 8px; }}
/* Pop-ups: a dimmed backdrop over the whole page, the card centred, rounded, and scrolling if tall with no bar showing. */
.sb-modal {{
  position: fixed !important; inset: 0; z-index: 1000; background: rgba(28, 27, 24, 0.45);
  display: flex; align-items: center; justify-content: center; padding: 16px !important;
}}
.sb-modal .sb-modal-card {{
  width: 100%; max-width: {PAGE_MAX_WIDTH}; max-height: 100%; overflow-y: auto; flex: none !important;
  border-radius: 20px !important; scrollbar-width: none;
}}
.sb-modal-card::-webkit-scrollbar {{ display: none; }}
.sb-sub-row {{ gap: 8px !important; }}
.sb-preset-tag {{ font-size: 14px; color: var(--sb-muted); margin-top: -4px; }}
/* The plan chooser: each preset's shares, why, and the research behind it. */
.sb-preset-split {{ font-size: 14px; font-weight: 500; font-variant-numeric: tabular-nums; margin-top: 2px; }}
.sb-source {{ font-size: 14px; color: var(--sb-muted); font-style: italic; margin-top: 4px; }}
.sb-head .sb-title {{ flex-wrap: wrap; row-gap: 6px; min-width: 0; }}
.sb-title-name {{ overflow-wrap: anywhere; }}

/* Hero: the month, one big number, where the money went and the split against the plan, and the duck. */
.sb-hero-top {{ align-items: center !important; flex-wrap: nowrap !important; }}
.sb-month-label {{ font-size: 16px; font-weight: 600; text-align: center; }}
/* Where the money went: the donut centred, its key in a centred row underneath. */
.sb-donut-row {{ display: flex; flex-direction: column; align-items: center; gap: 16px; margin: 20px 0 4px; }}
.sb-donut-row .sb-key {{ justify-content: center; }}
.sb-donut {{ position: relative; flex: none; }}
.sb-donut svg {{ display: block; }}
.sb-donut-middle {{
  position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center;
}}
.sb-donut-amount {{ font-family: var(--sb-serif); font-size: 40px; line-height: 1; font-variant-numeric: tabular-nums; }}
.sb-donut-label {{ font-size: 14px; color: var(--sb-muted); margin-top: 4px; }}
.sb-key {{ display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 14px; color: var(--sb-muted); }}
.sb-key span {{ display: inline-flex; align-items: center; gap: 6px; }}
.sb-key .sb-money {{ color: var(--sb-ink); }}
.sb-duck-says {{ display: flex; align-items: center; gap: 12px; margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--sb-line); }}
.sb-bubble {{
  position: relative; background: var(--sb-paper); border-radius: 14px; padding: 10px 14px; font-size: 14px; line-height: 1.4;
}}
.sb-bubble::before {{
  content: ""; position: absolute; left: -6px; top: 50%; width: 12px; height: 12px; background: var(--sb-paper);
  transform: translateY(-50%) rotate(45deg); border-radius: 2px;
}}
.sb-duck {{ flex: none; display: block; }}
.sb-bob {{ animation: sb-bob 3.2s ease-in-out infinite; transform-origin: 50% 90%; }}
@keyframes sb-bob {{ 0%, 100% {{ transform: translateY(0) rotate(0); }} 50% {{ transform: translateY(-3px) rotate(-2deg); }} }}
@media (prefers-reduced-motion: reduce) {{ .sb-bob {{ animation: none; }} }}

/* A line in a section: name, amount, edit, delete. Dividers run the full width. */
.sb-item {{ border-top: 1px solid var(--sb-line); padding-top: 10px; }}
.sb-line {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; font-size: 16px; }}
.sb-line-name {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}

/* Meters: thin, colour in the fill, words underneath. */
.sb-meter {{ height: 6px; background: var(--sb-line); border-radius: 999px; overflow: hidden; }}
.sb-meter > span {{ display: block; height: 100%; border-radius: 999px; }}
.sb-meter-row {{ display: grid; gap: 6px; }}
/* The split: each category's marker and amount, then its meter against the plan's percent. */
.sb-split {{ display: grid; gap: 16px; margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--sb-line); }}
.sb-split-row {{ display: grid; gap: 8px; }}
.sb-split-head {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
.sb-meter-label {{ font-size: 14px; display: flex; justify-content: space-between; gap: 8px; }}
.sb-meter-label > span:first-child {{ color: var(--sb-muted); }}

/* Buttons: pills. "+ Add" is a small green pill; edit, delete and the month arrows are quiet circles. */
.sb-add-button {{ min-width: 0 !important; padding: 8px 16px !important; font-size: 14px !important; height: 36px; flex: none !important; }}
.sb-icon {{
  border-radius: 999px !important; min-width: 40px !important; max-width: 40px; height: 40px; padding: 0 !important;
  border: none !important; background: transparent !important; color: var(--sb-muted) !important; font-size: 16px !important;
  flex: none !important;
}}
.sb-icon:hover {{ background: var(--sb-hover) !important; color: var(--sb-ink) !important; }}
.sb-nav {{ border: 1px solid var(--sb-line) !important; font-size: 20px !important; color: var(--sb-ink) !important; }}
.sb-panel {{ background: var(--sb-accent-soft); border-radius: 14px; padding: 14px !important; gap: 12px !important; }}
/* Gradio groups side-by-side boxes into one joined "form"; keep them as separate boxes on a clear background. */
.form {{ gap: 12px !important; background: transparent !important; border: none !important; box-shadow: none !important; overflow: visible !important; }}
.form > .block, .sb-panel .block {{ background: transparent !important; }}
/* Paired buttons share the row evenly; Gradio's 160px minimum would push the second one out on a phone. */
.sb-card .row > button.lg:not(.sb-icon):not(.sb-add-button) {{
  min-width: 0 !important; flex: 1 1 0 !important; padding-left: 12px !important; padding-right: 12px !important; white-space: nowrap;
}}
.sb-title + .sb-note {{ margin-top: 6px; }}

/* Tabs: a pill switcher. The tab you are on is a white pill in ink. */
.tab-wrapper {{ height: auto !important; margin-bottom: 16px; }}
.tab-container:not(.visually-hidden) {{
  height: auto !important; width: max-content; gap: 4px; padding: 4px; border-radius: 999px; background: var(--sb-paper-deep);
}}
.tab-container button {{
  height: auto !important; padding: 8px 22px !important; border: none !important; border-radius: 999px !important;
  font-size: 15px !important; font-weight: 600 !important; color: var(--sb-muted) !important; background: transparent !important;
}}
.tab-container button.selected {{ background: var(--sb-card) !important; color: var(--sb-ink) !important; box-shadow: 0 1px 3px rgb(28 27 24 / 0.12); }}
.tab-container button::after, .tab-container button.selected::after {{ display: none !important; }}

/* Filter pills: a Gradio radio styled like the tab switcher. */
/* One line always; on a narrow screen the row scrolls sideways inside itself rather than wrapping. */
.sb-pills .wrap {{
  display: flex; flex-wrap: nowrap; gap: 4px; padding: 4px; border-radius: 999px; background: var(--sb-paper-deep);
  width: max-content; max-width: 100%; overflow-x: auto; scrollbar-width: none;
}}
.sb-pills .wrap::-webkit-scrollbar {{ display: none; }}
.sb-pills label {{ flex: none; white-space: nowrap; }}
.sb-pills label {{
  margin: 0 !important; padding: 7px 16px !important; border: none !important; border-radius: 999px !important; background: transparent !important;
  font-size: 14px !important; font-weight: 600; color: var(--sb-muted) !important; box-shadow: none !important; cursor: pointer;
}}
.sb-pills label.selected {{ background: var(--sb-card) !important; color: var(--sb-ink) !important; box-shadow: 0 1px 3px rgb(28 27 24 / 0.12) !important; }}
.sb-pills input[type=radio] {{ display: none !important; }}
.sb-pills label > span {{ margin: 0 !important; }}

/* History: stat tiles, the column chart, its legend and table. */
.sb-tiles {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
.sb-tiles-4 {{ grid-template-columns: repeat(4, 1fr); }}
@media (max-width: 480px) {{ .sb-tiles-4 {{ grid-template-columns: repeat(2, 1fr); }} }}
.sb-tile {{ background: var(--sb-card); border: 1px solid var(--sb-line); border-radius: 16px; padding: 14px 16px; }}
.sb-tile-value {{ font-size: 24px; font-weight: 600; margin-top: 4px; letter-spacing: -0.01em; }}
.sb-tile-value.sb-over {{ color: var(--sb-over); }}
@media (max-width: 480px) {{
  .sb-tiles {{ gap: 8px; }}
  .sb-tile {{ padding: 12px; }}
  .sb-tile-value {{ font-size: 18px; }}
}}
.sb-chart {{ margin-top: 20px; }}
.sb-plot {{ position: relative; height: 220px; margin: 8px 0 0 52px; }}
.sb-grid {{ position: absolute; left: 0; right: 0; border-top: 1px solid var(--sb-line); }}
.sb-grid > span {{
  position: absolute; right: calc(100% + 8px); transform: translateY(-50%); font-size: 12px; color: var(--sb-muted);
  white-space: nowrap; font-variant-numeric: tabular-nums;
}}
.sb-cols {{ position: absolute; inset: 0; display: grid; align-items: end; }}
.sb-month-col {{ position: relative; display: flex; justify-content: center; align-items: flex-end; gap: 2px; height: 100%; min-width: 0; }}
.sb-month-col:hover, .sb-month-col:focus-visible {{ z-index: 2; }}
.sb-stack {{ position: relative; width: 24px; max-width: 42%; display: flex; flex-direction: column-reverse; gap: 2px; }}
.sb-seg {{ min-height: 2px; outline-offset: 1px; }}
.sb-seg-top {{ border-radius: 4px 4px 0 0; }}
.sb-seg:hover {{ filter: brightness(1.12); }}
.sb-zoomable {{ cursor: pointer; }}
/* One tooltip per month, beside the column so it stays inside the plot; right-half months open to the left. */
.sb-tip {{
  display: none; position: absolute; top: 0; left: calc(50% + 18px); z-index: 3; width: max-content; max-width: 220px;
  padding: 10px 12px; border-radius: 12px; background: var(--sb-card); border: 1px solid var(--sb-line);
  box-shadow: 0 4px 16px rgb(28 27 24 / 0.14); font-size: 14px; pointer-events: none; text-align: left;
}}
.sb-tip-left {{ left: auto; right: calc(50% + 18px); }}
.sb-month-col:hover .sb-tip, .sb-month-col:focus-visible .sb-tip {{ display: block; }}
/* Phones are too narrow to open beside a middle month: pin the card to the plot's far top corner instead. */
@media (max-width: 480px) {{
  .sb-month-col {{ position: static; }}
  .sb-tip {{ left: auto; right: 0; }}
  .sb-tip-left {{ left: 0; right: auto; }}
}}
.sb-tip-month {{ font-weight: 600; margin-bottom: 6px; }}
.sb-tip-row {{ display: flex; align-items: center; gap: 8px; line-height: 1.6; }}
.sb-tip-row i {{ flex: none; width: 10px; height: 10px; border-radius: 3px; }}
.sb-tip-row span {{ flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--sb-muted); }}
.sb-tip-row b {{ font-weight: 600; font-variant-numeric: tabular-nums; }}
.sb-tip-total {{ border-top: 1px solid var(--sb-line); margin-top: 4px; padding-top: 4px; }}
.sb-back {{ margin-top: 8px; padding: 0; border: none; background: none; font-size: 14px; font-weight: 600; color: var(--sb-accent-dark); cursor: pointer; }}
.sb-callout {{ font-size: 14px; font-weight: 600; margin-top: 8px; }}
.sb-xaxis {{ display: grid; margin: 8px 0 0 52px; font-size: 12px; color: var(--sb-muted); text-align: center; }}
.sb-xaxis span {{ white-space: nowrap; }}
.sb-hide-desktop {{ visibility: hidden; }}
@media (max-width: 480px) {{
  .sb-hide-desktop {{ visibility: visible; }}
  .sb-hide-phone {{ visibility: hidden; }}
}}
.sb-legend {{ display: flex; flex-wrap: wrap; gap: 6px 16px; margin-top: 16px; font-size: 14px; color: var(--sb-muted); }}
.sb-legend i {{ display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; }}
.sb-legend button {{ padding: 0; border: none; background: none; font: inherit; color: inherit; cursor: pointer; }}
.sb-legend button:hover {{ color: var(--sb-ink); }}
.sb-hidden {{ display: none !important; }}
.sb-details {{ margin-top: 16px; border-top: 1px solid var(--sb-line); padding-top: 12px; }}
.sb-details summary {{ cursor: pointer; font-size: 14px; font-weight: 600; color: var(--sb-accent-dark); }}
.sb-table-wrap {{ overflow-x: auto; }}
.sb-table, .sb-table tr {{ border: none !important; }}
.sb-table td, .sb-table th {{ white-space: nowrap; }}
.sb-table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 14px; font-variant-numeric: tabular-nums; }}
.sb-table th, .sb-table td {{ text-align: right !important; padding: 8px 4px !important; border: none !important; border-bottom: 1px solid var(--sb-line) !important; background: none !important; }}
.sb-table th {{ color: var(--sb-muted); font-weight: 500; }}
.sb-table th:first-child, .sb-table td:first-child {{ text-align: left !important; }}
.sb-top-items {{ margin-top: 8px; }}
.sb-item-row {{
  display: grid; grid-template-columns: 1fr auto auto; gap: 12px; align-items: baseline; padding: 10px 0;
  border-top: 1px solid var(--sb-line); font-size: 16px;
}}

/* Sign in: the full mallard on top, everything centred. */
.sb-auth {{ max-width: 440px; margin: 24px auto 0 !important; }}
.sb-auth-top {{ display: flex; flex-direction: column; align-items: center; text-align: center; gap: 8px; }}
.sb-auth-top .sb-wordmark {{ font-size: 40px; margin-top: 4px; }}
.sb-auth-top .sb-note {{ font-size: 16px; }}
.sb-full {{ width: 100% !important; }}
.sb-auth-form {{ gap: 12px !important; margin-top: 8px; }}
.sb-link-button {{
  border: none !important; background: transparent !important; box-shadow: none !important;
  color: var(--sb-accent-dark) !important; font-size: 15px !important; font-weight: 600 !important;
}}
.sb-link-button:hover {{ text-decoration: underline; }}
.sb-danger {{ background: transparent !important; box-shadow: none !important; border-style: dashed !important; }}
"""


# ---------- The mallard ----------

# Detailed and colourful, for the sign-in card. Faces right.
DUCK_FULL = f"""<svg class="sb-duck sb-bob" viewBox="0 0 220 170" width="{{size}}" height="{{size_h}}" role="img" aria-label="Mallard duck mascot">
<defs>
  <linearGradient id="sbHead" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#2FA36B"/><stop offset="0.45" stop-color="{DUCK_HEAD}"/><stop offset="0.8" stop-color="#0E3B2A"/><stop offset="1" stop-color="#3A2F6B"/>
  </linearGradient>
  <linearGradient id="sbBody" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#D4CFC5"/><stop offset="1" stop-color="#A39D91"/>
  </linearGradient>
  <linearGradient id="sbBreast" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#9A5430"/><stop offset="1" stop-color="{DUCK_BREAST}"/>
  </linearGradient>
  <linearGradient id="sbWing" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#7F57C9"/><stop offset="1" stop-color="#2F4FC4"/>
  </linearGradient>
</defs>
<ellipse cx="110" cy="152" rx="92" ry="10" fill="#D9ECF2"/>
<path d="M44 150 q12 -6 24 0 q12 6 24 0 M128 152 q12 -6 24 0 q12 6 24 0" fill="none" stroke="#B9DCE7" stroke-width="2.5" stroke-linecap="round"/>
<path d="M92 144 l-7 10 l13 -2 z M118 145 l-5 10 l12 -3 z" fill="#E88B2E"/>
<path d="M20 93 L38 85 L36 100 Z" fill="#F4F2ED" stroke="#D8D3C9" stroke-width="1"/>
<path d="M28 90 C46 84 70 80 104 80 C132 80 150 84 160 92 C176 104 178 126 160 138 C146 146 110 147 80 145 C58 143 42 132 34 116 C30 108 28 98 28 90 Z" fill="url(#sbBody)"/>
<path d="M28 90 C38 86 48 84 58 85 C55 94 47 101 36 105 C31 100 28 95 28 90 Z" fill="#26241F"/>
<path d="M47 86 C40 77 44 69 51 70 C56 71 56 78 50 79" fill="none" stroke="#26241F" stroke-width="3.5" stroke-linecap="round"/>
<path d="M70 128 C92 134 124 134 150 128 M62 135 C88 141 126 141 148 135" fill="none" stroke="#9D978B" stroke-width="1.1" stroke-linecap="round" opacity="0.6"/>
<path d="M134 86 C158 84 178 100 178 118 C178 130 168 138 156 138 C160 124 154 102 134 86 Z" fill="url(#sbBreast)"/>
<path d="M130 96 C112 87 72 86 46 99 C60 113 94 121 122 116 C134 112 138 102 130 96 Z" fill="#8F887C"/>
<path d="M60 106 C72 107 86 109 98 108 C90 115 72 116 57 111 Z" fill="url(#sbWing)"/>
<path d="M60 106 C72 107 86 109 98 108 M57 111 C72 116 90 115 98 108" fill="none" stroke="#FFFFFF" stroke-width="1.6" stroke-linecap="round"/>
<path d="M80 96 C96 92 112 93 124 99 M72 101 C92 96 112 98 126 105 M104 112 C112 112 120 110 126 106" fill="none" stroke="#7A7468" stroke-width="1.3" stroke-linecap="round"/>
<path d="M135 95 C133 79 139 65 151 58 L179 62 C179 78 173 91 163 99 Z" fill="url(#sbHead)"/>
<ellipse cx="163" cy="50" rx="27" ry="23" fill="url(#sbHead)"/>
<ellipse cx="155" cy="40" rx="10" ry="4.5" fill="#FFFFFF" opacity="0.22" transform="rotate(-20 155 40)"/>
<path d="M136 93 C146 100 158 100 167 93" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round"/>
<path d="M183 47 C196 44 208 49 210 56 C205 62 193 62 182 59 Z" fill="{DUCK_BILL}"/>
<path d="M184 54 C194 55 202 55 208 55" fill="none" stroke="#C9971F" stroke-width="1.4" stroke-linecap="round"/>
<circle cx="208.5" cy="55.5" r="1.8" fill="#3A2A10"/>
<circle cx="173" cy="44" r="3.6" fill="#121110"/>
<circle cx="174.3" cy="42.7" r="1.2" fill="#FFFFFF"/>
</svg>"""

# Simplified for the logo and the duck's speech bubble: flat colours, readable at 24px. Faces right.
DUCK_MARK = f"""<svg class="sb-duck" viewBox="0 0 64 64" width="{{size}}" height="{{size}}" role="img" aria-label="Sliced Bread duck">
<path d="M5 33 C14 29 22 28 32 28 C44 28 53 33 55 41 C57 50 49 56 38 56 L20 56 C11 56 6 47 5 33 Z" fill="{DUCK_BODY}"/>
<path d="M42 31 C52 33 58 41 56 48 C54 53 48 55 44 53 C47 46 47 37 42 31 Z" fill="{DUCK_BREAST}"/>
<path d="M13 31 C9 28 10 23 14 23" fill="none" stroke="#26241F" stroke-width="2.6" stroke-linecap="round"/>
<path d="M40 31 C40 24 43 20 47 19 L53 22 C53 27 51 31 47 34 Z" fill="{DUCK_HEAD}"/>
<circle cx="47" cy="17" r="11" fill="{DUCK_HEAD}"/>
<path d="M40 31 C43.5 33.5 47.5 33.5 51 30.5" fill="none" stroke="#FFFFFF" stroke-width="2.4" stroke-linecap="round"/>
<path d="M56 14.5 C60.5 13.5 63.5 15.5 63.5 18 C61.5 20 58.5 20 56 19 Z" fill="{DUCK_BILL}"/>
<circle cx="50.5" cy="14" r="1.8" fill="#121110"/>
</svg>"""


def duck_full(size=160):
    return DUCK_FULL.replace("{size}", str(size)).replace("{size_h}", str(round(size * 170 / 220)))


def duck_mark(size=32):
    return DUCK_MARK.replace("{size}", str(size))


# ---------- HTML pieces (escape everything the user typed) ----------

def shades(color, count, darkest=DARKEST_MIX, lightest=LIGHTEST_MIX):
    """count shades of one hex colour, darkest first: the History zoom's biggest line to its smallest."""
    if count == 1:
        return [color]
    red, green, blue = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    result = []
    for index in range(count):
        mix = -darkest + (darkest + lightest) * index / (count - 1)  # below 0 toward black, above toward white
        target = 255 if mix > 0 else 0
        channels = (round(value + (target - value) * abs(mix)) for value in (red, green, blue))
        result.append("#" + "".join(f"{channel:02X}" for channel in channels))
    return result


def subcategory_colors(user_budget):
    """Each subcategory's colour: a shade of its category's, in page order."""
    colors = {}
    for category, color in CATEGORY_COLORS.items():
        keys = [sub["key"] for sub in budget.subcategories_in(user_budget, category)]
        colors.update(zip(keys, shades(color, len(keys), SUBCATEGORY_DARKEST_MIX, SUBCATEGORY_LIGHTEST_MIX)))
    return colors


def donut_svg(amounts, income):
    """The hero ring: one segment per category with money in it, income in the middle. A grey ring when empty."""
    radius = (DONUT_SIZE - DONUT_STROKE) / 2
    circumference = 2 * math.pi * radius
    centre = DONUT_SIZE / 2
    whole = sum(amounts.values())
    parts = [(category, cents) for category, cents in amounts.items() if cents]
    ring = (
        f'<circle cx="{centre}" cy="{centre}" r="{radius}" fill="none" stroke="{LINE}" stroke-width="{DONUT_STROKE}"></circle>'
    )
    start = 0.0
    segments = ""
    for category, cents in parts:
        length = cents / whole * circumference
        gap = DONUT_GAP if len(parts) > 1 else 0
        title = f"{budget.CATEGORY_NAMES[category]} {budget.format_money(cents)} ({round(cents * 100 / whole)}%)"
        segments += (
            f'<circle cx="{centre}" cy="{centre}" r="{radius}" fill="none" stroke="{CATEGORY_COLORS[category]}" '
            f'stroke-width="{DONUT_STROKE}" stroke-dasharray="{max(length - gap, 0):.2f} {circumference:.2f}" '
            f'stroke-dashoffset="{-start:.2f}" transform="rotate(-90 {centre} {centre})"><title>{title}</title></circle>'
        )
        start += length
    return (
        f'<div class="sb-donut"><svg width="{DONUT_SIZE}" height="{DONUT_SIZE}" viewBox="0 0 {DONUT_SIZE} {DONUT_SIZE}" '
        f'role="img" aria-label="Where the money went">{ring if not parts else ""}{segments}</svg>'
        f'<div class="sb-donut-middle"><span class="sb-donut-amount">{budget.format_money(income)}</span>'
        '<span class="sb-donut-label">income</span></div></div>'
    )


def dot(color):
    return f'<span class="sb-dot" style="background:{color}"></span>'


def marker(category):
    """Which of the four categories something counts toward: a small pill with the category's dot and name."""
    return f'<span class="sb-marker">{dot(CATEGORY_COLORS[category])}{budget.CATEGORY_NAMES[category]}</span>'


def money(cents):
    return f'<span class="sb-money">{budget.format_money(cents)}</span>'


def meter_html(result, label_left=""):
    """A meter in plain ink with its words. Empty when no target is set."""
    if result["state"] == "none":
        return ""
    width = max(result["fraction"] * 100, 2)
    return (
        f'<div class="sb-meter-row"><div class="sb-meter"><span style="width:{width:.1f}%;'
        f'background:{INK}"></span></div>'
        f'<div class="sb-meter-label"><span>{html.escape(label_left)}</span><span>{html.escape(result["label"])}</span></div></div>'
    )


def line_html(name, cents):
    return f'<div class="sb-line"><span class="sb-line-name">{html.escape(name)}</span>{money(cents)}</div>'
