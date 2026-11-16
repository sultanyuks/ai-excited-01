#!/usr/bin/env python3
"""Heart of the Vortex - procedural neon galaxy with a blazing heart core.

Pure Python 3 stdlib, deterministic, pixel-by-pixel rendering.
Writes entry.png (768x768 RGB PNG) to $MAKEFUN_OUTPUT_DIR.
"""
import math
import os
import random
import struct
import zlib

W = 768
H = 768
CX = W / 2.0
CY = H / 2.0


def clamp(v, lo=0.0, hi=1.0):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def ramp(t, stops):
    """Interpolate through a list of (pos, (r,g,b)) stops, t in [0,1]."""
    if t <= stops[0][0]:
        return stops[0][1]
    for i in range(1, len(stops)):
        p1, c1 = stops[i]
        p0, c0 = stops[i - 1]
        if t <= p1:
            f = (t - p0) / (p1 - p0)
            return (c0[0] + (c1[0] - c0[0]) * f,
                    c0[1] + (c1[1] - c0[1]) * f,
                    c0[2] + (c1[2] - c0[2]) * f)
    return stops[-1][1]


ARM_STOPS = [
    (0.00, (88.0, 32.0, 190.0)),    # deep violet
    (0.35, (225.0, 38.0, 165.0)),   # magenta
    (0.65, (255.0, 105.0, 25.0)),   # hot orange
    (1.00, (255.0, 215.0, 90.0)),   # gold
]

HEART_STOPS = [
    (0.00, (255.0, 252.0, 245.0)),  # hot white
    (0.22, (255.0, 170.0, 185.0)),  # light pink
    (0.50, (255.0, 55.0, 120.0)),   # hot pink
    (1.00, (205.0, 8.0, 42.0)),     # deep red
]


def render():
    pixels = bytearray(W * H * 3)
    sin = math.sin
    log = math.log
    exp = math.exp
    sqrt = math.sqrt
    atan2 = math.atan2

    # ---- Pass 1: background + spiral galaxy + core glow ----
    for y in range(H):
        ny = (y - CY) / 384.0
        row = y * W * 3
        for x in range(W):
            nx = (x - CX) / 384.0
            r2 = nx * nx + ny * ny
            r = sqrt(r2)

            # Deep indigo-black background, radial gradient + vignette
            bt = clamp(r / 1.25)
            br = 17.0 + (3.0 - 17.0) * bt
            bg_ = 11.0 + (3.0 - 11.0) * bt
            bb = 38.0 + (10.0 - 38.0) * bt
            vig = 1.0 - 0.38 * clamp((r - 0.62) / 0.75) ** 2
            br *= vig
            bg_ *= vig
            bb *= vig

            # Spiral arms: sin(3*theta + k*log(r))
            if r > 0.015:
                theta = atan2(ny, nx)
                phase = 3.0 * theta - 8.0 * log(r + 0.15)
                s = 0.5 + 0.5 * sin(phase)
            else:
                s = 0.5
            fall = exp(-r * 1.85)
            arm = (s ** 7) * 1.55 + (s ** 3) * 0.30
            inten = arm * fall

            # Diffuse violet disk glow
            disk = exp(-r * 3.2) * 0.09

            # Arm colour from ramp: gold core -> orange -> magenta -> violet
            t = clamp(1.12 - r)
            cr, cg, cb = ramp(t, ARM_STOPS)

            rr = br + cr * inten + 70.0 * disk
            gg = bg_ + cg * inten + 30.0 * disk
            bb2 = bb + cb * inten + 150.0 * disk

            # Bright white-gold core glow
            core = exp(-r2 / 0.016) + 0.38 * exp(-r2 / 0.11)
            rr += 255.0 * core
            gg += 232.0 * core
            bb2 += 175.0 * core

            i = row + x * 3
            pixels[i] = 255 if rr > 255 else (0 if rr < 0 else int(rr))
            pixels[i + 1] = 255 if gg > 255 else (0 if gg < 0 else int(gg))
            pixels[i + 2] = 255 if bb2 > 255 else (0 if bb2 < 0 else int(bb2))

    # ---- Stars: ~250 deterministic soft gaussian dots, a few flared ----
    rng = random.Random(1234)
    stars = []
    for _ in range(250):
        sx = rng.uniform(0, W - 1)
        sy = rng.uniform(0, H - 1)
        sigma = rng.uniform(0.7, 1.7)
        bright = rng.uniform(90, 255)
        tint = rng.random()
        flare = rng.random() < 0.07
        stars.append((sx, sy, sigma, bright, tint, flare))

    for sx, sy, sigma, bright, tint, flare in stars:
        if tint < 0.6:
            tc = (1.0, 1.0, 1.0)
        elif tint < 0.8:
            tc = (0.75, 0.85, 1.0)
        else:
            tc = (1.0, 0.88, 0.70)
        rad = int(sigma * 4) + 1
        x0, x1 = max(0, int(sx) - rad), min(W - 1, int(sx) + rad)
        y0, y1 = max(0, int(sy) - rad), min(H - 1, int(sy) + rad)
        inv = 1.0 / (2.0 * sigma * sigma)
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                d2 = (xx - sx) ** 2 + (yy - sy) ** 2
                g = bright * exp(-d2 * inv)
                if g < 1.0:
                    continue
                i = (yy * W + xx) * 3
                v = pixels[i] + g * tc[0]
                pixels[i] = 255 if v > 255 else int(v)
                v = pixels[i + 1] + g * tc[1]
                pixels[i + 1] = 255 if v > 255 else int(v)
                v = pixels[i + 2] + g * tc[2]
                pixels[i + 2] = 255 if v > 255 else int(v)
        if flare:
            length = 14
            cx_i, cy_i = int(sx), int(sy)
            for d in range(-length, length + 1):
                if d == 0:
                    continue
                fade = bright * 0.55 * (1.0 - abs(d) / (length + 1.0)) ** 2
                for xx, yy in ((cx_i + d, cy_i), (cx_i, cy_i + d)):
                    if 0 <= xx < W and 0 <= yy < H:
                        i = (yy * W + xx) * 3
                        v = pixels[i] + fade * tc[0]
                        pixels[i] = 255 if v > 255 else int(v)
                        v = pixels[i + 1] + fade * tc[1]
                        pixels[i + 1] = 255 if v > 255 else int(v)
                        v = pixels[i + 2] + fade * tc[2]
                        pixels[i + 2] = 255 if v > 255 else int(v)

    # ---- Pass 2: heart, halo and gold pulse rings (central region) ----
    HS = 112.0  # heart scale, px per heart unit
    R_BOX = 265
    xa, xb = int(CX) - R_BOX, int(CX) + R_BOX
    ya, yb = int(CY) - R_BOX, int(CY) + R_BOX
    for y in range(ya, yb):
        dy = y - CY
        for x in range(xa, xb):
            dx = x - CX
            rp = sqrt(dx * dx + dy * dy)
            i = (y * W + x) * 3
            rr = float(pixels[i])
            gg = float(pixels[i + 1])
            bb2 = float(pixels[i + 2])

            # Heart halo: warm pink glow, tapered to zero before the
            # edge of this pass's box so no square seam can appear
            taper = clamp((R_BOX - rp) / 70.0)
            halo = exp(-(rp * rp) / (2.0 * 125.0 * 125.0)) * 0.38 * taper
            rr += 255.0 * halo
            gg += 60.0 * halo
            bb2 += 110.0 * halo

            # Two thin gold pulse rings, brightness sweeping around
            # the circle so they feel like an outgoing pulse
            theta = atan2(dy, dx)
            sweep = 0.30 + 0.70 * (0.5 + 0.5 * sin(theta + 0.8))
            for ring_r, ring_a in ((162.0, 0.60), (202.0, 0.45)):
                rd = rp - ring_r
                ring = exp(-(rd * rd) / (2.0 * 1.5 * 1.5)) * ring_a * sweep
                rr += 255.0 * ring
                gg += 198.0 * ring
                bb2 += 70.0 * ring

            # Heart shape: (x^2+y^2-1)^3 - x^2*y^3 < 0, y flipped upright
            hx = dx / HS
            hy = -dy / HS
            q = hx * hx + hy * hy - 1.0
            f = q * q * q - hx * hx * hy * hy * hy
            alpha = clamp(0.5 - f * 7.0)
            if alpha > 0.0:
                # hot spot sits slightly above centre, so the lower
                # half and bottom tip shade deeper red
                hd = sqrt(hx * hx + (hy - 0.18) * (hy - 0.18))
                st = clamp((hd / 1.05) ** 1.5)
                hr, hg, hb = ramp(st, HEART_STOPS)
                # inner incandescence
                boost = (1.0 - st) * 12.0
                hr += boost
                hg += boost
                hb += boost
                rr = rr * (1.0 - alpha) + hr * alpha
                gg = gg * (1.0 - alpha) + hg * alpha
                bb2 = bb2 * (1.0 - alpha) + hb * alpha

            # Silhouette definition: a soft dark seam just outside the
            # heart, and a blazing rim of light tracing the curve
            if f > 0.0:
                seam = exp(-(f * f) / 0.002) * 0.30
                rr *= (1.0 - seam)
                gg *= (1.0 - seam)
                bb2 *= (1.0 - seam)
            rim = exp(-(f * f) / 0.0018) * 0.55
            if rim > 0.01:
                rr = rr * (1.0 - rim) + 255.0 * rim
                gg = gg * (1.0 - rim) + 175.0 * rim
                bb2 = bb2 * (1.0 - rim) + 195.0 * rim

            pixels[i] = 255 if rr > 255 else (0 if rr < 0 else int(rr))
            pixels[i + 1] = 255 if gg > 255 else (0 if gg < 0 else int(gg))
            pixels[i + 2] = 255 if bb2 > 255 else (0 if bb2 < 0 else int(bb2))

    return pixels


def write_png(pixels, path):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw.extend(pixels[y * stride:(y + 1) * stride])
    compressed = zlib.compress(bytes(raw), 6)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        c += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return c

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", compressed)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    pixels = render()
    write_png(pixels, os.path.join(out_dir, "entry.png"))


if __name__ == "__main__":
    main()
