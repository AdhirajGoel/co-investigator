# Co-Investigator architecture figure

`architecture.svg` is the editable original; text remains text and all artwork is vector. `architecture.pdf` is a vector export at 183 mm width, and `architecture.png` is its 200 dpi raster preview. The single system graph connects scientist control and feedback, host-followed scientific skills, executable utilities, persistent files, and requested independent review. Its smallest labels are approximately 7.9 pt at the exported width. Its caption and implementation mapping are in [architecture.md](../architecture.md).

Regenerate the SVG using Python's standard library:

```sh
python3 docs/figures/render_architecture.py
```

To regenerate all three formats, use an isolated environment with the optional figure dependencies and an installed Poppler `pdftoppm` command:

```sh
python3 -m venv .venv-figures
.venv-figures/bin/python -m pip install -r docs/figures/requirements-figure.txt
.venv-figures/bin/python docs/figures/render_architecture.py --render
```

The script checks geometry coordinates, XML structure, required content, and rendered file signatures. Inspect the rendered image after editing labels or layout. Helvetica/Arial text is used; font availability and renderer versions can affect appearance. The tested export used Python 3.11, ReportLab 4.4.10, svglib 1.5.1, and Poppler 26.04.0. The layout is authored in the Python source, so regenerate from that file after changing it; direct SVG edits are overwritten on regeneration.

The PDF and PNG are optional exports. Neither these rendering packages nor Poppler is required merely to view the checked-in figure or use workspace setup.
