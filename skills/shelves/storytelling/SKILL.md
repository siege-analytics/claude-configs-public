---
name: shelf-storytelling
description: Router for storytelling / data-presentation book skills. Dispatches to storytelling-with-data, tufte-data-viz, or animation-at-work based on task signals. Read this when communicating findings, building decks, designing or implementing charts, or animating in slides/web.
disable-model-invocation: false
---

# Storytelling — Shelf

## Trigger table

| Task signal | Book to read |
|---|---|
| Charts, decks, presenting findings to a non-technical audience (Knaflic) | [skill:storytelling-with-data] |
| Tufte chart-implementation rules — data-ink ratio, direct labels, range-frame axes, per-library config (Recharts / ECharts / Chart.js / matplotlib / Plotly / D3) | [skill:tufte-data-viz] |
| When and how to use animation in interfaces and slides (Nabors) | [skill:animation-at-work] |

## Disambiguation: Tufte vs Knaflic

Both `tufte-data-viz` and `storytelling-with-data` cover data visualization, but at different layers — load both for a full data-presentation task:

- **`storytelling-with-data` (Knaflic)** — the *upstream framing* layer: who is the audience, what action do they need to take, what's the Big Idea, what story does the data tell, what chart type fits the message. Read this first when the task is "I have findings, how do I present them?"
- **`tufte-data-viz` (Caylent / Tufte)** — the *implementation* layer: given the chart is needed, what is the highest-data-ink, lowest-chartjunk version? Per-library config rules for the major chart libraries. Read this when the task is "I'm writing chart code" or "this chart looks busy — how do I clean it?"

The pair compose without overlap. A typical workflow: Knaflic decides the message + chart type; Tufte decides the chart's visual implementation.

## Attribution

`storytelling-with-data` + `animation-at-work` imported from ZLStas/skills; `tufte-data-viz` imported from caylent/tufte-data-viz (MIT). See per-skill footers and `THIRD_PARTY_NOTICES.md`.
