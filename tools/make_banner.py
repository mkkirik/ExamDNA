"""Generate assets/banner.svg — the animated README banner (pure SVG, no external fonts or hosts).

The double helix is drawn procedurally; each base-pair rung pulses with a staggered
SMIL animation. Colours follow the logo: charcoal #1e1f22 / signal red #e3141b.
Run: python tools/make_banner.py
"""

import math
from pathlib import Path

W, H = 1280, 320
OUT = Path(__file__).resolve().parent.parent / "assets" / "banner.svg"
RED, RED2, INK, GREY = "#e3141b", "#ff5a5f", "#f5f5f7", "#a1a1aa"


def helix(x0: float, x1: float, cy: float, amp: float, turns: float, n: int):
    parts = []
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        phase = 2 * math.pi * turns * t
        y1 = cy + amp * math.sin(phase)
        y2 = cy - amp * math.sin(phase)
        depth = (math.cos(phase) + 1) / 2  # 0 back .. 1 front
        delay = f"{(i * 0.09):.2f}s"
        if i % 2 == 0:
            parts.append(
                f'<line x1="{x:.1f}" y1="{y1:.1f}" x2="{x:.1f}" y2="{y2:.1f}" stroke="#ffffff" stroke-opacity="0.16" stroke-width="2.5" stroke-linecap="round">'
                f'<animate attributeName="stroke-opacity" values="0.08;0.42;0.08" dur="2.8s" begin="{delay}" repeatCount="indefinite"/></line>'
            )
        r1 = 3.5 + 3.0 * depth
        r2 = 3.5 + 3.0 * (1 - depth)
        parts.append(f'<circle cx="{x:.1f}" cy="{y1:.1f}" r="{r1:.1f}" fill="url(#red)"/>')
        parts.append(f'<circle cx="{x:.1f}" cy="{y2:.1f}" r="{r2:.1f}" fill="#d4d4d8" fill-opacity="{0.45 + 0.5 * (1 - depth):.2f}"/>')
    return "\n    ".join(parts)


def main() -> None:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="ExamDNA — Reverse-engineer exams. Mutate questions. Compile new assessments.">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#16171a"/>
      <stop offset="0.55" stop-color="#1e1f23"/>
      <stop offset="1" stop-color="#2a0d10"/>
    </linearGradient>
    <linearGradient id="red" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{RED2}"/>
      <stop offset="1" stop-color="{RED}"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.82" cy="0.5" r="0.45">
      <stop offset="0" stop-color="{RED}" stop-opacity="0.35"/>
      <stop offset="1" stop-color="{RED}" stop-opacity="0"/>
    </radialGradient>
    <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
      <path d="M32 0H0V32" fill="none" stroke="#ffffff" stroke-opacity="0.035" stroke-width="1"/>
    </pattern>
    <clipPath id="card"><rect width="{W}" height="{H}" rx="22"/></clipPath>
  </defs>
  <g clip-path="url(#card)">
    <rect width="{W}" height="{H}" fill="url(#bg)"/>
    <rect width="{W}" height="{H}" fill="url(#grid)"/>
    <rect width="{W}" height="{H}" fill="url(#glow)"/>
    <g>
    {helix(940, 1236, 160, 80, 1.6, 30)}
      <animateTransform attributeName="transform" type="translate" values="0 0; -6 0; 0 0" dur="6s" repeatCount="indefinite"/>
    </g>
    <g font-family="'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif">
      <text x="72" y="150" font-size="92" font-weight="800" fill="{INK}" letter-spacing="-2">Exam<tspan fill="url(#red)">DNA</tspan></text>
      <text x="76" y="200" font-size="23" font-weight="500" fill="{GREY}">Reverse-engineer exams. Mutate questions. Compile new assessments.</text>
      <g font-size="15" font-weight="600">
        <rect x="76" y="232" width="176" height="34" rx="17" fill="#ffffff" fill-opacity="0.07" stroke="#ffffff" stroke-opacity="0.14"/>
        <text x="164" y="254" text-anchor="middle" fill="{INK}">Claude Agent Skill</text>
        <rect x="264" y="232" width="206" height="34" rx="17" fill="#ffffff" fill-opacity="0.07" stroke="#ffffff" stroke-opacity="0.14"/>
        <text x="367" y="254" text-anchor="middle" fill="{INK}">9 mutation operators</text>
        <rect x="482" y="232" width="202" height="34" rx="17" fill="{RED}" fill-opacity="0.18" stroke="{RED}" stroke-opacity="0.65"/>
        <text x="583" y="254" text-anchor="middle" fill="#ffd6d7">Deterministic checks</text>
      </g>
    </g>
  </g>
</svg>
"""
    OUT.write_bytes(svg.encode("utf-8"))
    print(f"wrote {OUT.relative_to(OUT.parent.parent)} ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
