#!/usr/bin/env python3
"""
Generate a live, rotating 3D spiral galaxy rendered in terminal ASCII art as a
SMIL-animated SVG flipbook. Zero JavaScript -- runs natively in GitHub's <img> tag.

Simulates ~25,000 galactic particles (core bulge, logarithmic spiral arms, and
interstellar disk dust), projects them with 3D inclination & perspective, and
cycles through a 360-degree rotation loop.
"""

import html
import math
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "samarpit-ascii.svg")

COLS = 100
ROWS = 53
CELL_W = 8
CELL_H = 15
ASPECT = CELL_W / CELL_H  # Character aspect ratio ~0.5333

RAMP = " .`:-=+*s#%@"

PAD = 20
TITLEBAR_H = 30
STATUS_H = 30
ART_W = COLS * CELL_W
ART_H = ROWS * CELL_H
CANVAS_W = ART_W + PAD * 2
CANVAS_H = TITLEBAR_H + ART_H + STATUS_H + PAD

BG = "#0d1117"
BG2 = "#111722"
FRAME = "#30363d"
TITLE_TEXT = "#7d8590"
INK = "#c9d1d9"
CYAN = "#58a6ff"
GREEN = "#39d353"

# Animation parameters
N_FRAMES = 28
LOOP_DUR = 4.20  # seconds per 360-deg rotation
REVEAL_DUR = 0.80  # initial wipe reveal


def generate_galaxy(n_particles=25000, seed=42):
    np.random.seed(seed)

    # 1. Galactic Bulge / Core (dense spheroid)
    n_core = n_particles // 5
    core_r = np.random.exponential(scale=3.2, size=n_core)
    core_th = np.random.uniform(0, 2 * np.pi, size=n_core)
    core_z = np.random.normal(0, 1.8, size=n_core)
    core_x = core_r * np.cos(core_th)
    core_y = core_r * np.sin(core_th)
    core_lum = np.random.uniform(2.6, 4.8, size=n_core) * np.exp(-core_r / 4.0)

    # 2. Main Spiral Arms (2 prominent arms with logarithmic winding)
    n_arms = 2
    n_arm_stars = int(n_particles * 0.60)
    arm_choice = np.random.choice(n_arms, size=n_arm_stars)
    r_arm = np.random.uniform(3.0, 42.0, size=n_arm_stars)
    th_arm = (
        arm_choice * np.pi
        + 2.65 * np.log(r_arm / 2.4 + 1.0)
        + np.random.normal(0, 0.22, size=n_arm_stars)
    )
    z_arm = np.random.normal(0, 1.3 * np.exp(-r_arm / 35.0), size=n_arm_stars)
    arm_x = r_arm * np.cos(th_arm)
    arm_y = r_arm * np.sin(th_arm)
    arm_lum = np.random.uniform(1.0, 2.3, size=n_arm_stars) * np.exp(-r_arm / 48.0)

    # 3. Inter-arm disk stars & halo dust
    n_disk = n_particles - n_core - n_arm_stars
    r_disk = np.random.uniform(2.0, 40.0, size=n_disk)
    th_disk = np.random.uniform(0, 2 * np.pi, size=n_disk)
    z_disk = np.random.normal(0, 1.0, size=n_disk)
    disk_x = r_disk * np.cos(th_disk)
    disk_y = r_disk * np.sin(th_disk)
    disk_lum = np.random.uniform(0.3, 0.9, size=n_disk) * np.exp(-r_disk / 35.0)

    x = np.concatenate([core_x, arm_x, disk_x])
    y = np.concatenate([core_y, arm_y, disk_y])
    z = np.concatenate([core_z, z_arm, z_disk])
    lum = np.concatenate([core_lum, arm_lum, disk_lum])

    return x, y, z, lum


def render_frame(x, y, z, lum, rot_angle):
    inc = math.radians(58)  # Inclination tilt (58 deg)
    pa = math.radians(24)   # Position angle in sky (24 deg)

    # Rotate around galactic polar axis (Z)
    cos_r, sin_r = np.cos(rot_angle), np.sin(rot_angle)
    xr = x * cos_r - y * sin_r
    yr = x * sin_r + y * cos_r
    zr = z

    # Tilt around X by inclination
    cos_i, sin_i = np.cos(inc), np.sin(inc)
    yt = yr * cos_i - zr * sin_i
    zt = yr * sin_i + zr * cos_i
    xt = xr

    # Rotate by position angle in sky
    cos_p, sin_p = np.cos(pa), np.sin(pa)
    xp = xt * cos_p - yt * sin_p
    yp = xt * sin_p + yt * cos_p

    # Perspective projection
    dist = 85.0
    fov = dist / (dist + zt)
    xp = xp * fov
    yp = yp * fov

    # Map to ASCII grid
    scale = (COLS * 0.44) / 40.0
    cx = COLS / 2.0 + xp * scale
    cy = ROWS / 2.0 - yp * (scale * ASPECT)

    grid = np.zeros((ROWS, COLS), dtype=float)
    col_idx = np.round(cx).astype(int)
    row_idx = np.round(cy).astype(int)

    valid = (col_idx >= 0) & (col_idx < COLS) & (row_idx >= 0) & (row_idx < ROWS)
    for r_i, c_i, l in zip(row_idx[valid], col_idx[valid], lum[valid]):
        grid[r_i, c_i] += l

    vmax = np.percentile(grid[grid > 0], 97) if np.any(grid > 0) else 1.0

    lines = []
    for r_i in range(ROWS):
        chars = []
        for c_i in range(COLS):
            v = grid[r_i, c_i]
            if v <= 0.045:
                chars.append(" ")
            else:
                val = min(1.0, v / vmax)
                idx = int(val * (len(RAMP) - 1))
                chars.append(RAMP[idx])
        lines.append("".join(chars))

    return lines


def build_svg(frames):
    art_top = TITLEBAR_H + PAD * 0.35
    fs = CELL_H * 0.88
    n = len(frames)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" '
        f'viewBox="0 0 {CANVAS_W} {CANVAS_H}" font-family="ui-monospace, SFMono-Regular, '
        f'Menlo, Consolas, monospace">',
        '<defs>'
        f'<linearGradient id="gbg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/>'
        '</linearGradient></defs>',
        f'<rect width="{CANVAS_W}" height="{CANVAS_H}" rx="12" fill="url(#gbg)"/>',
        f'<rect x="0.5" y="0.5" width="{CANVAS_W-1}" height="{CANVAS_H-1}" rx="12" '
        f'fill="none" stroke="{FRAME}" stroke-width="1"/>',
        f'<line x1="0" y1="{TITLEBAR_H}" x2="{CANVAS_W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>',
    ]

    # MacOS window dots
    for i, dot in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dot}"/>')
    parts.append(
        f'<text x="{CANVAS_W/2}" y="{TITLEBAR_H/2 + 4}" fill="{TITLE_TEXT}" font-size="12" '
        f'text-anchor="middle">samarpit@github: ~$ ./galaxy.sh --3d-live</text>'
    )

    def render_frame_rows(rows):
        out_rows = []
        for ry, line in enumerate(rows):
            s = line.rstrip()
            if not s.strip():
                continue
            lead = len(s) - len(s.lstrip(" "))
            body = s[lead:]
            x = PAD + lead * CELL_W
            y = art_top + ry * CELL_H + CELL_H * 0.74
            out_rows.append(
                f'<text xml:space="preserve" x="{x:.1f}" y="{y:.1f}" font-size="{fs:.1f}" '
                f'textLength="{len(body)*CELL_W:.1f}" lengthAdjust="spacing">{html.escape(body)}</text>'
            )
        return "".join(out_rows)

    # Initial wipe-in reveal
    parts.append(
        f'<clipPath id="gwipe"><rect x="{PAD}" y="{art_top:.1f}" height="{ART_H:.1f}" width="0">'
        f'<animate attributeName="width" from="0" to="{ART_W}" begin="0s" '
        f'dur="{REVEAL_DUR:.2f}s" fill="freeze"/></rect></clipPath>'
    )
    parts.append(
        f'<g clip-path="url(#gwipe)" fill="{INK}">{render_frame_rows(frames[0])}'
        f'<set attributeName="opacity" to="0" begin="{REVEAL_DUR:.2f}s"/></g>'
    )

    # Animated flipbook groups (discrete calcMode opacity)
    for i, frame in enumerate(frames):
        if i == 0:
            vals, kt = "1;0", f"0;{1/n:.5f}"
        else:
            vals, kt = "0;1;0", f"0;{i/n:.5f};{(i+1)/n:.5f}"

        anim = (
            f'<animate attributeName="opacity" calcMode="discrete" values="{vals}" '
            f'keyTimes="{kt}" dur="{LOOP_DUR:.2f}s" begin="{REVEAL_DUR:.2f}s" '
            f'repeatCount="indefinite"/>'
        )

        rows_markup = render_frame_rows(frame)
        parts.append(
            f'<g fill="{INK}" opacity="0">{rows_markup}{anim}</g>'
        )

    # Status bar with a steady blinking cursor
    status_line_y = TITLEBAR_H + ART_H + PAD * 0.35
    status_y = status_line_y + 19
    parts.append(f'<line x1="0" y1="{status_line_y:.1f}" x2="{CANVAS_W}" y2="{status_line_y:.1f}" stroke="{FRAME}"/>')
    parts.append(
        f'<text x="{PAD}" y="{status_y:.1f}" fill="{TITLE_TEXT}" font-size="13">'
        f'samarpit@github:~$ orbit <tspan fill="{CYAN}">3D spiral galaxy active</tspan>'
        f' <tspan fill="{TITLE_TEXT}">[360&#176; continuous]</tspan></text>'
    )
    parts.append(
        f'<rect x="{PAD+365}" y="{status_y-12:.1f}" width="8" height="14" fill="{INK}">'
        f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" '
        f'dur="1s" repeatCount="indefinite"/></rect>'
    )

    parts.append("</svg>")
    return "".join(parts)


def main():
    print(f"Simulating 25,000 galactic stars across {N_FRAMES} rotation frames...")
    x, y, z, lum = generate_galaxy(n_particles=25000)

    frames = []
    for k in range(N_FRAMES):
        angle = (2 * np.pi * k) / N_FRAMES
        frames.append(render_frame(x, y, z, lum, angle))

    svg = build_svg(frames)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"wrote {OUT} ({len(svg)/1024:.1f} KB; {CANVAS_W}x{CANVAS_H}; {N_FRAMES} frames)")


if __name__ == "__main__":
    main()
