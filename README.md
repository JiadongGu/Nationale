# Two-Lens Optical System Simulator

A small Tkinter + matplotlib GUI that simulates a thin-lens, paraxial
two-lens system. Sliders let you change the object distance, object
height, both focal lengths, and the lens separation in real time. The
ray diagram and a numerical readout of intermediate/final image
positions, magnifications, and orientation update on every change.

## Run

```bash
pip install matplotlib numpy
python two_lens_sim.py
```

## Controls

| Variable | Meaning |
|---|---|
| `s₁` | Object distance in front of lens 1 (cm) |
| `h₁` | Object height (cm); negative flips the object |
| `f₁` | Focal length of lens 1 — positive = converging, negative = diverging |
| `f₂` | Focal length of lens 2 |
| `d`  | Distance between the two lenses |

## Conventions

Light travels left → right. Lens 1 is at `x = 0`, lens 2 at `x = d`.
Object distances are positive when the object is on the incoming side.
Image distances are positive when on the outgoing side (real image),
negative for virtual images. The total magnification `M = m₁ · m₂`
is negative when the final image is inverted.

The diagram traces three principal rays from the tip of the object:

- one parallel to the axis (refracts through `F₁'`),
- one through the center of lens 1 (undeviated there),
- one through the front focal point `F₁` (exits parallel).

Each ray is then refracted at lens 2 using `u' = u − y/f₂`.
