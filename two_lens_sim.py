"""Two-lens optical system simulator.

Thin-lens, paraxial approximation. Sign convention: light travels +x;
object distances are positive when the object is on the incoming side of
the lens, image distances are positive when on the outgoing side.
"""

import tkinter as tk
from tkinter import ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


def thin_lens_image(s, f):
    """Return (s_prime, magnification) for object distance s, focal length f."""
    if abs(s - f) < 1e-9:
        return float("inf"), float("inf")
    s_prime = 1.0 / (1.0 / f - 1.0 / s)
    m = -s_prime / s
    return s_prime, m


def trace_system(s1, f1, f2, d, h1):
    """Propagate object through lens 1 then lens 2."""
    s1p, m1 = thin_lens_image(s1, f1)
    h_intermediate = m1 * h1 if np.isfinite(m1) else float("inf")

    # Object distance for lens 2: positive if intermediate image is to the
    # left of lens 2 (real object for lens 2).
    s2 = d - s1p
    s2p, m2 = thin_lens_image(s2, f2) if np.isfinite(s2) else (float("inf"), float("inf"))
    h_final = m2 * h_intermediate if np.isfinite(m2) and np.isfinite(h_intermediate) else float("inf")
    m_total = m1 * m2 if np.isfinite(m1) and np.isfinite(m2) else float("inf")

    return {
        "s1": s1, "s1p": s1p, "m1": m1, "h_int": h_intermediate,
        "s2": s2, "s2p": s2p, "m2": m2,
        "h_final": h_final, "m_total": m_total,
    }


def refract_at_lens(x_lens, f, ray_in_origin, ray_in_dir):
    """Given a ray hitting a thin lens at x=x_lens, return outgoing direction.

    Uses the matrix-style rule: a ray at height y with slope u becomes
    slope u' = u - y/f after the lens.
    """
    ox, oy = ray_in_origin
    dx, dy = ray_in_dir
    if abs(dx) < 1e-12:
        return None
    t = (x_lens - ox) / dx
    y_at = oy + t * dy
    slope_in = dy / dx
    slope_out = slope_in - y_at / f
    return (x_lens, y_at), (1.0, slope_out)


class TwoLensApp:
    def __init__(self, root):
        self.root = root
        root.title("Two-Lens Optical System Simulator")

        self.vars = {
            "s1": tk.DoubleVar(value=15.0),
            "h1": tk.DoubleVar(value=2.0),
            "f1": tk.DoubleVar(value=10.0),
            "f2": tk.DoubleVar(value=8.0),
            "d":  tk.DoubleVar(value=25.0),
        }

        self._build_controls()
        self._build_plot()
        self.update()

    def _build_controls(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.grid(row=0, column=0, sticky="ns")

        ttk.Label(frame, text="Two-Lens Simulator",
                  font=("TkDefaultFont", 12, "bold")).grid(
            row=0, column=0, columnspan=3, pady=(0, 10))

        sliders = [
            ("Object distance s₁ (cm)", "s1", 1.0, 50.0),
            ("Object height h₁ (cm)",    "h1", -5.0, 5.0),
            ("Focal length f₁ (cm)",     "f1", -30.0, 30.0),
            ("Focal length f₂ (cm)",     "f2", -30.0, 30.0),
            ("Lens separation d (cm)",        "d",  1.0, 60.0),
        ]

        for i, (label, key, lo, hi) in enumerate(sliders, start=1):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w")
            scale = ttk.Scale(frame, from_=lo, to=hi, orient="horizontal",
                              length=240, variable=self.vars[key],
                              command=lambda _v: self.update())
            scale.grid(row=i, column=1, padx=6)
            entry = ttk.Entry(frame, textvariable=self.vars[key], width=7)
            entry.grid(row=i, column=2)
            entry.bind("<Return>", lambda _e: self.update())
            entry.bind("<FocusOut>", lambda _e: self.update())

        ttk.Separator(frame, orient="horizontal").grid(
            row=99, column=0, columnspan=3, sticky="ew", pady=10)

        self.readout = tk.Text(frame, width=42, height=14, font=("TkFixedFont", 10),
                               relief="flat", background=self.root.cget("background"))
        self.readout.grid(row=100, column=0, columnspan=3, sticky="w")
        self.readout.configure(state="disabled")

        ttk.Button(frame, text="Reset", command=self.reset).grid(
            row=101, column=0, columnspan=3, pady=(8, 0))

    def _build_plot(self):
        self.fig = Figure(figsize=(8.5, 5.5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().grid(row=0, column=1, sticky="nsew")
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

    def reset(self):
        defaults = {"s1": 15.0, "h1": 2.0, "f1": 10.0, "f2": 8.0, "d": 25.0}
        for k, v in defaults.items():
            self.vars[k].set(v)
        self.update()

    def update(self):
        try:
            s1 = float(self.vars["s1"].get())
            h1 = float(self.vars["h1"].get())
            f1 = float(self.vars["f1"].get())
            f2 = float(self.vars["f2"].get())
            d  = float(self.vars["d"].get())
        except (ValueError, tk.TclError):
            return

        if abs(f1) < 1e-3 or abs(f2) < 1e-3 or s1 <= 0 or d <= 0:
            return

        result = trace_system(s1, f1, f2, d, h1)
        self._draw(s1, h1, f1, f2, d, result)
        self._write_readout(f1, f2, d, result)

    def _draw(self, s1, h1, f1, f2, d, r):
        ax = self.ax
        ax.clear()

        # Lens positions: lens 1 at x=0, lens 2 at x=d. Object at x=-s1.
        x_l1, x_l2 = 0.0, d
        x_obj = -s1

        # Decide x-range
        s1p, s2p = r["s1p"], r["s2p"]
        candidates = [x_obj, x_l2, x_l2 + (s2p if np.isfinite(s2p) else 0)]
        if np.isfinite(s1p):
            candidates.append(x_l1 + s1p)
        x_min = min(candidates) - 5
        x_max = max(candidates) + 5

        h_max = max(abs(h1), abs(r["h_int"]) if np.isfinite(r["h_int"]) else 0,
                    abs(r["h_final"]) if np.isfinite(r["h_final"]) else 0, 1.0)
        y_lim = h_max * 1.6

        # Optical axis
        ax.axhline(0, color="gray", lw=0.8)

        # Lenses
        self._draw_lens(ax, x_l1, f1, y_lim, "L₁")
        self._draw_lens(ax, x_l2, f2, y_lim, "L₂")

        # Focal points
        for x, f in ((x_l1, f1), (x_l2, f2)):
            ax.plot([x - f, x + f], [0, 0], "k+", markersize=8)

        # Object arrow
        ax.annotate("", xy=(x_obj, h1), xytext=(x_obj, 0),
                    arrowprops=dict(arrowstyle="->", color="tab:blue", lw=2))
        ax.text(x_obj, h1 * 1.1 if h1 >= 0 else h1 * 1.1,
                "Object", color="tab:blue", ha="center",
                va="bottom" if h1 >= 0 else "top", fontsize=9)

        # Intermediate image
        if np.isfinite(s1p) and np.isfinite(r["h_int"]):
            x_int = x_l1 + s1p
            ax.annotate("", xy=(x_int, r["h_int"]), xytext=(x_int, 0),
                        arrowprops=dict(arrowstyle="->", color="tab:orange",
                                        lw=1.5, linestyle="--"))
            ax.text(x_int, r["h_int"] * 1.1 if r["h_int"] >= 0 else r["h_int"] * 1.1,
                    "I₁", color="tab:orange", ha="center",
                    va="bottom" if r["h_int"] >= 0 else "top", fontsize=9)

        # Final image
        if np.isfinite(s2p) and np.isfinite(r["h_final"]):
            x_fin = x_l2 + s2p
            ax.annotate("", xy=(x_fin, r["h_final"]), xytext=(x_fin, 0),
                        arrowprops=dict(arrowstyle="->", color="tab:red", lw=2.5))
            ax.text(x_fin, r["h_final"] * 1.1 if r["h_final"] >= 0 else r["h_final"] * 1.1,
                    "Final image", color="tab:red", ha="center",
                    va="bottom" if r["h_final"] >= 0 else "top", fontsize=9)

        self._draw_principal_rays(ax, x_obj, h1, x_l1, f1, x_l2, f2, r,
                                  x_min, x_max)

        ax.set_xlim(x_min, x_max)
        ax.set_ylim(-y_lim, y_lim)
        ax.set_xlabel("x (cm)")
        ax.set_ylabel("y (cm)")
        ax.set_title("Two-lens system — principal rays")
        ax.grid(True, alpha=0.3)
        self.fig.tight_layout()
        self.canvas.draw_idle()

    @staticmethod
    def _draw_lens(ax, x, f, y_lim, label):
        color = "tab:green" if f > 0 else "tab:purple"
        h = y_lim * 0.9
        ax.plot([x, x], [-h, h], color=color, lw=1.2)
        if f > 0:
            ax.plot(x, h, marker="^", color=color, markersize=8)
            ax.plot(x, -h, marker="v", color=color, markersize=8)
        else:
            ax.plot(x, h, marker="v", color=color, markersize=8)
            ax.plot(x, -h, marker="^", color=color, markersize=8)
        ax.text(x, -y_lim * 0.97, label, color=color, ha="center",
                va="top", fontsize=10, fontweight="bold")

    def _draw_principal_rays(self, ax, x_obj, h1, x_l1, f1, x_l2, f2, r,
                             x_min, x_max):
        """Three principal rays from the tip of the object through both lenses."""
        if abs(h1) < 1e-9:
            return

        rays = []

        # Ray 1: parallel to axis, refracts through F' of lens 1
        rays.append(self._propagate_ray(
            (x_obj, h1), (1.0, 0.0), x_l1, f1, x_l2, f2))

        # Ray 2: through center of lens 1 (undeviated by L1)
        slope2 = (0 - h1) / (x_l1 - x_obj)
        rays.append(self._propagate_ray(
            (x_obj, h1), (1.0, slope2), x_l1, f1, x_l2, f2))

        # Ray 3: through front focal point F of lens 1, exits parallel
        if abs(x_l1 - f1 - x_obj) > 1e-6:
            slope3 = (0 - h1) / ((x_l1 - f1) - x_obj)
            rays.append(self._propagate_ray(
                (x_obj, h1), (1.0, slope3), x_l1, f1, x_l2, f2))

        x_end = x_max
        if np.isfinite(r["s2p"]):
            x_end = max(x_end, x_l2 + r["s2p"] + 2)

        colors = ["tab:cyan", "tab:olive", "tab:brown"]
        for ray, color in zip(rays, colors):
            self._plot_ray(ax, ray, x_obj, x_l1, x_l2, x_end, color)

    @staticmethod
    def _propagate_ray(origin, direction, x_l1, f1, x_l2, f2):
        """Return list of segments [(p0, p1), ...] for a ray through both lenses."""
        segments = []
        p0 = origin
        d0 = direction

        # Segment 1: object to lens 1
        hit1, dir1 = refract_at_lens(x_l1, f1, p0, d0)
        segments.append((p0, hit1, d0))

        # Segment 2: lens 1 to lens 2
        hit2, dir2 = refract_at_lens(x_l2, f2, hit1, dir1)
        segments.append((hit1, hit2, dir1))

        # Segment 3: after lens 2 (open-ended)
        segments.append((hit2, None, dir2))
        return segments

    @staticmethod
    def _plot_ray(ax, segments, x_obj, x_l1, x_l2, x_end, color):
        # Solid: object -> L1 -> L2 -> x_end
        (p0, p1, _) = segments[0]
        ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=color, lw=1)
        (p1, p2, _) = segments[1]
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=color, lw=1)
        (p2, _, dir3) = segments[2]
        dx, dy = dir3
        if abs(dx) > 1e-12:
            t = (x_end - p2[0]) / dx
            x3 = p2[0] + t * dx
            y3 = p2[1] + t * dy
            ax.plot([p2[0], x3], [p2[1], y3], color=color, lw=1)

    def _write_readout(self, f1, f2, d, r):
        def fmt(x, unit="cm"):
            if not np.isfinite(x):
                return "  ∞ (at infinity)"
            return f"{x:+8.3f} {unit}"

        kind1 = "real" if r["s1p"] > 0 else "virtual"
        kind2 = "real" if (np.isfinite(r["s2p"]) and r["s2p"] > 0) else "virtual"
        orient = "inverted" if r["m_total"] < 0 else "upright"
        mag_word = "magnified" if abs(r["m_total"]) > 1 else "reduced"

        lines = [
            f"Lens 1   f₁ = {f1:+.2f} cm   ({'converging' if f1>0 else 'diverging'})",
            f"Lens 2   f₂ = {f2:+.2f} cm   ({'converging' if f2>0 else 'diverging'})",
            f"Lens separation d = {d:.2f} cm",
            "-" * 40,
            f"After L₁:  s₁' = {fmt(r['s1p'])}   ({kind1})",
            f"           m₁  = {r['m1']:+.3f}",
            f"           h'  = {fmt(r['h_int'])}",
            "",
            f"At L₂:    s₂  = {fmt(r['s2'])}",
            f"After L₂:  s₂' = {fmt(r['s2p'])}   ({kind2})",
            f"           m₂  = {r['m2']:+.3f}",
            "",
            f"Total mag M = {r['m_total']:+.3f}  ({orient}, {mag_word})",
            f"Final image height = {fmt(r['h_final'])}",
        ]
        self.readout.configure(state="normal")
        self.readout.delete("1.0", tk.END)
        self.readout.insert(tk.END, "\n".join(lines))
        self.readout.configure(state="disabled")


def main():
    root = tk.Tk()
    TwoLensApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
