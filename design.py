"""Toast, the Sliced Bread design system: tokens, the Gradio theme and the CSS. See PLAN.md section 5.

The one rule: crust means "you can press it". Crust marks controls only, never money or status.
Nothing in app.py sets a colour or size by hand; it uses the classes defined here.
"""

import html

import gradio as gr

import budget

# ---------- Tokens ----------

PAPER = "#FAF8F4"  # page background
CARD = "#FFFFFF"  # section cards
INK = "#1F1D1A"  # all text, all money
MUTED = "#6B655C"  # secondary labels, 5.4:1 on paper
LINE = "#E7E2D9"  # borders, dividers, empty meter track
CRUST = "#9A5B1E"  # controls and focus ring; white text on it is 5.4:1
CRUST_DARK = "#7E4916"  # control hover
CRUST_SOFT = "#F6EBDD"  # wash behind the open add row
GOOD = "#2F7D4F"  # meter under 90%, savings bar
WARN = "#D99A00"  # meter 90-100% (fill only, never text)
OVER = "#B42318"  # meter over 100%, "Over budget" text

# Fills only (section dots, the stacked bar), never text.
SECTION_COLORS = {
    "income": INK,
    "necessities": "#3B6FB5",
    "discretionary": "#8E4FA8",
    "travel": "#1E8C93",
    "investments": GOOD,
}
METER_COLORS = {"good": GOOD, "warn": WARN, "over": OVER}

FONT_TEXT = "Inter"
FONT_MONEY = "JetBrains Mono"
PAGE_MAX_WIDTH = "640px"

# Crust and paper as Gradio colour ramps, so built-in components pick them up.
CRUST_RAMP = gr.themes.Color(
    c50="#FBF4EA", c100=CRUST_SOFT, c200="#EBD3B5", c300="#DDB58A", c400="#C88F58", c500="#B07235",
    c600=CRUST, c700=CRUST_DARK, c800="#633912", c900="#4A2B0E", c950="#2E1B09", name="crust",
)
PAPER_RAMP = gr.themes.Color(
    c50=PAPER, c100="#F3F0EA", c200=LINE, c300="#D3CCC0", c400="#A39C90", c500="#7D776D",
    c600=MUTED, c700="#4A4640", c800="#2F2C28", c900=INK, c950="#141311", name="paper",
)


def build_theme():
    """The Gradio theme. Light only: every dark-mode value is copied from its light twin."""
    theme = gr.themes.Base(
        primary_hue=CRUST_RAMP,
        secondary_hue=CRUST_RAMP,
        neutral_hue=PAPER_RAMP,
        font=[gr.themes.GoogleFont(FONT_TEXT), "ui-sans-serif", "system-ui", "sans-serif"],
        font_mono=[gr.themes.GoogleFont(FONT_MONEY), "ui-monospace", "Consolas", "monospace"],
        radius_size=gr.themes.sizes.radius_md,
        text_size=gr.themes.sizes.text_md,
    ).set(
        body_background_fill=PAPER,
        body_text_color=INK,
        body_text_color_subdued=MUTED,
        background_fill_primary=CARD,
        background_fill_secondary=PAPER,
        border_color_primary=LINE,
        block_background_fill=CARD,
        block_border_color=LINE,
        block_shadow="none",
        input_background_fill=CARD,
        input_border_color=LINE,
        input_border_color_focus=CRUST,
        button_primary_background_fill=CRUST,
        button_primary_background_fill_hover=CRUST_DARK,
        button_primary_text_color="#FFFFFF",
        button_primary_border_color=CRUST,
        button_secondary_background_fill=CARD,
        button_secondary_background_fill_hover=CRUST_SOFT,
        button_secondary_text_color=INK,
        button_secondary_border_color=LINE,
        button_cancel_background_fill=OVER,
        button_cancel_background_fill_hover="#8F1C13",
        button_cancel_text_color="#FFFFFF",
    )
    for name in list(vars(theme)):
        if name.endswith("_dark"):
            setattr(theme, name, getattr(theme, name.removesuffix("_dark")))
    return theme


CSS = f"""
:root {{
  --sb-paper: {PAPER}; --sb-card: {CARD}; --sb-ink: {INK}; --sb-muted: {MUTED}; --sb-line: {LINE};
  --sb-crust: {CRUST}; --sb-crust-dark: {CRUST_DARK}; --sb-crust-soft: {CRUST_SOFT};
  --sb-over: {OVER};
  --sb-money: '{FONT_MONEY}', ui-monospace, Consolas, monospace;
}}

/* One centred column, phone first. */
.gradio-container {{ width: 100% !important; max-width: {PAGE_MAX_WIDTH} !important; margin: 0 auto !important; padding: 16px !important; }}
.gradio-container .main {{ padding: 0 !important; }}
footer {{ display: none !important; }}
:focus-visible {{ outline: 3px solid var(--sb-crust) !important; outline-offset: 2px; }}

/* Type scale: 14 / 16 / 20 / 24 / 32 / 40. Nothing smaller than 14. The hero is 40, or 32 on a phone. */
.sb-brand {{ font-size: 24px; font-weight: 700; letter-spacing: -0.01em; }}
.sb-subtitle {{ font-size: 16px; color: var(--sb-muted); margin-top: 4px; }}
.sb-hero {{ font-size: 40px; line-height: 1.1; font-weight: 700; letter-spacing: -0.02em; text-wrap: balance; }}
.sb-hero.sb-over {{ color: var(--sb-over); }}
@media (max-width: 480px) {{ .sb-hero {{ font-size: 32px; }} }}
.sb-title {{ font-size: 20px; font-weight: 600; display: flex; align-items: center; gap: 8px; }}
.sb-note {{ font-size: 14px; color: var(--sb-muted); }}
.sb-money {{ font-family: var(--sb-money); font-variant-numeric: tabular-nums; white-space: nowrap; }}
.sb-dot {{ width: 10px; height: 10px; border-radius: 999px; display: inline-block; flex: none; }}

/* Cards: 12px radius, 16px padding, one shadow. */
.sb-card {{
  background: var(--sb-card); border: 1px solid var(--sb-line); border-radius: 12px;
  padding: 16px !important; gap: 8px !important; box-shadow: 0 1px 2px rgb(0 0 0 / 0.06);
}}
.sb-card .html-container, .sb-card .prose {{ padding: 0 !important; }}
.sb-row {{ align-items: center !important; gap: 8px !important; flex-wrap: nowrap !important; }}
.sb-grow {{ flex: 1 1 auto !important; min-width: 0 !important; }}
.sb-head {{ display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }}
.sb-head .sb-money {{ font-size: 16px; }}
.sb-line {{
  display: flex; justify-content: space-between; gap: 12px; font-size: 16px;
  padding: 8px 0; border-top: 1px solid var(--sb-line);
}}
.sb-line-name {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}

/* Meters: colour in the fill, words beside it. */
.sb-meter {{ height: 8px; background: var(--sb-line); border-radius: 999px; overflow: hidden; }}
.sb-meter > span {{ display: block; height: 100%; border-radius: 999px; }}
.sb-meter-row {{ display: grid; gap: 4px; }}
.sb-split {{ display: grid; gap: 12px; margin-top: 12px; }}
.sb-meter-label {{ font-size: 14px; color: var(--sb-ink); display: flex; justify-content: space-between; gap: 8px; }}

/* Where the money went: one stacked bar and its key. */
.sb-bar {{ display: flex; height: 16px; border-radius: 999px; overflow: hidden; background: var(--sb-line); margin: 16px 0 8px; }}
.sb-key {{ display: flex; flex-wrap: wrap; gap: 4px 16px; font-size: 14px; }}
.sb-key span {{ display: inline-flex; align-items: center; gap: 6px; }}

/* Pill controls: + and x. Crust on the +, quiet on the x. */
.sb-plus {{ border-radius: 999px !important; min-width: 40px !important; max-width: 40px; height: 40px; padding: 0 !important; font-size: 20px !important; }}
.sb-x {{
  border-radius: 999px !important; min-width: 32px !important; max-width: 32px; height: 32px; padding: 0 !important;
  border: none !important; background: transparent !important; color: var(--sb-muted) !important; font-size: 16px !important;
}}
.sb-x:hover {{ background: var(--sb-crust-soft) !important; color: var(--sb-ink) !important; }}
.sb-add {{ background: var(--sb-crust-soft); border-radius: 8px; padding: 12px !important; gap: 8px !important; }}
.sb-month {{ align-items: center !important; justify-content: space-between; flex-wrap: nowrap !important; }}
.sb-month .sb-title {{ justify-content: center; }}
.sb-gap {{ gap: 12px !important; }}
"""


# ---------- HTML pieces (escape everything the user typed) ----------

def dot(section):
    return f'<span class="sb-dot" style="background:{SECTION_COLORS[section]}"></span>'


def money(cents):
    return f'<span class="sb-money">{budget.format_money(cents)}</span>'


def meter_html(result, label_left=""):
    """A limit meter with its words. Empty string when no limit is set."""
    if result["state"] == "none":
        return ""
    width = max(result["fraction"] * 100, 2)
    return (
        f'<div class="sb-meter-row"><div class="sb-meter"><span style="width:{width:.1f}%;'
        f'background:{METER_COLORS[result["state"]]}"></span></div>'
        f'<div class="sb-meter-label"><span>{html.escape(label_left)}</span><span>{html.escape(result["label"])}</span></div></div>'
    )


def progress_html(saved, goal):
    """The savings goal bar: always the good colour, it only fills."""
    width = max(min(saved / goal, 1) * 100, 2)
    return (
        f'<div class="sb-meter-row"><div class="sb-meter"><span style="width:{width:.1f}%;background:{GOOD}"></span></div>'
        f'<div class="sb-meter-label"><span>Savings goal</span><span class="sb-money">'
        f'{budget.format_money(saved)} of {budget.format_money(goal)}</span></div></div>'
    )


def line_html(name, cents):
    return f'<div class="sb-line"><span class="sb-line-name">{html.escape(name)}</span>{money(cents)}</div>'
