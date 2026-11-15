"""Figura del flujo CRISP-DM con los módulos de cada fase (D2).

Sin datos ni resultados: solo dibuja la estructura del flujo. Los nombres de módulo deben coincidir con
``src/`` o ``scripts/`` y con la tabla de módulos del paper (lo comprueban las pruebas).

Uso::

    python -m scripts.figura_pipeline            # escribe docs/figuras/pipeline-crisp-dm.{pdf,png}
    python -m scripts.figura_pipeline --out ruta
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Phase:
    name: str                      # nombre completo de la fase CRISP-DM
    label: str                     # nombre con saltos de línea para la figura
    modules: tuple[str, ...] = ()
    note: str = ""                 # texto libre cuando la fase no tiene módulo


PHASES: tuple[Phase, ...] = (
    Phase("Comprensión del negocio", "Comprensión\ndel negocio", note="Requisitos\ny alcance"),
    Phase("Comprensión de datos", "Comprensión\nde datos", ("inspect_data", "analisis_fase1")),
    Phase("Preparación", "Preparación",
          ("preprocessing", "data_loader", "episodes", "feature_engineering")),
    Phase("Modelado", "Modelado", ("split_data", "baseline", "train")),
    Phase("Evaluación", "Evaluación", ("predict", "alerts", "evaluate", "figuras_evaluacion")),
    Phase("Despliegue", "Despliegue", ("replay", "mitigation_simulator")),
)

CROSS_CUTTING: tuple[str, ...] = ("experiment",)
CROSS_CUTTING_NOTE = "registro de ejecuciones y bloqueo de la prueba final"

FIGURE_NAME = "pipeline-crisp-dm"


def all_modules() -> list[str]:
    """Todos los módulos que menciona la figura, sin repetir y en orden."""
    seen: list[str] = []
    for m in [m for p in PHASES for m in p.modules] + list(CROSS_CUTTING):
        if m not in seen:
            seen.append(m)
    return seen


def build_pipeline_figure(out_dir: Path) -> list[Path]:
    """Escribe ``pipeline-crisp-dm.pdf`` (vectorial) y ``.png`` en ``out_dir`` y devuelve sus rutas."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    per_row = 3
    rows = [PHASES[i:i + per_row] for i in range(0, len(PHASES), per_row)]
    width = 7.2
    margin, gap_x, gap_y = 0.08, 0.30, 0.34
    head_h, line_h, pad = 0.30, 0.135, 0.12
    mod_h = line_h * max(len(p.modules) for p in PHASES) + pad
    bar_h, bar_gap = 0.30, 0.16
    height = 2 * margin + len(rows) * (head_h + mod_h) + (len(rows) - 1) * gap_y + bar_gap + bar_h

    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.axis("off")

    box_w = (width - 2 * margin - gap_x * (per_row - 1)) / per_row
    edge, head_fill, mod_fill = "#33415c", "#dbe4f0", "#ffffff"
    centers: dict[int, tuple[float, float, float, float]] = {}  # fase -> (x, y_head, box_w, y_mod)

    for r, row in enumerate(rows):
        y_head = height - margin - r * (head_h + mod_h + gap_y) - head_h
        y_mod = y_head - mod_h
        for c, ph in enumerate(row):
            idx = r * per_row + c
            x = margin + c * (box_w + gap_x)
            centers[idx] = (x, y_head, box_w, y_mod)
            ax.add_patch(FancyBboxPatch((x, y_head), box_w, head_h, boxstyle="round,pad=0,rounding_size=0.04",
                                        facecolor=head_fill, edgecolor=edge, linewidth=1.0))
            ax.text(x + box_w / 2, y_head + head_h / 2, f"{idx + 1}. {ph.name}", ha="center", va="center",
                    fontsize=7.0, fontweight="bold", color="#111111")
            ax.add_patch(FancyBboxPatch((x, y_mod), box_w, mod_h, boxstyle="round,pad=0,rounding_size=0.04",
                                        facecolor=mod_fill, edgecolor=edge, linewidth=0.8))
            if ph.modules:
                top_line = y_mod + mod_h / 2 + line_h * (len(ph.modules) - 1) / 2  # bloque centrado
                for j, m in enumerate(ph.modules):
                    ax.text(x + box_w / 2, top_line - line_h * j, m, ha="center", va="center",
                            fontsize=6.6, family="monospace", color="#111111")
            else:
                ax.text(x + box_w / 2, y_mod + mod_h / 2, ph.note.replace("\n", " "), ha="center", va="center",
                        fontsize=7.0, style="italic", color="#111111")
            if c < len(row) - 1:  # flecha hacia la fase siguiente de la misma fila
                ax.add_patch(FancyArrowPatch((x + box_w + 0.02, y_head + head_h / 2),
                                             (x + box_w + gap_x - 0.02, y_head + head_h / 2),
                                             arrowstyle="-|>", mutation_scale=8, linewidth=1.1, color=edge))

    # Conector del final de la primera fila al inicio de la segunda (fase 3 -> fase 4).
    x3, y3_head, w3, y3_mod = centers[per_row - 1]
    x4, y4_head, _, _ = centers[per_row]
    y_mid = y3_mod - gap_y / 2
    ax.plot([x3 + w3 / 2, x3 + w3 / 2], [y3_mod - 0.01, y_mid], color=edge, linewidth=1.1)
    ax.plot([x3 + w3 / 2, x4 + w3 / 2], [y_mid, y_mid], color=edge, linewidth=1.1)
    ax.add_patch(FancyArrowPatch((x4 + w3 / 2, y_mid), (x4 + w3 / 2, y4_head + head_h + 0.02),
                                 arrowstyle="-|>", mutation_scale=8, linewidth=1.1, color=edge))

    bar_y = margin
    ax.add_patch(FancyBboxPatch((margin, bar_y), width - 2 * margin, bar_h,
                                boxstyle="round,pad=0,rounding_size=0.04",
                                facecolor="#eef2f7", edgecolor=edge, linewidth=0.8, linestyle="--"))
    ax.text(width / 2, bar_y + bar_h / 2, f"Transversal:  {CROSS_CUTTING[0]}  ·  {CROSS_CUTTING_NOTE}",
            ha="center", va="center", fontsize=7.0, color="#111111")

    paths: list[Path] = []
    for ext, meta in (("pdf", {"CreationDate": None, "Creator": "matplotlib"}), ("png", {"Software": None})):
        path = out_dir / f"{FIGURE_NAME}.{ext}"
        fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.03, metadata=meta)
        paths.append(path)
    plt.close(fig)
    return paths


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Figura del flujo CRISP-DM con los módulos de cada fase.")
    ap.add_argument("--out", default="docs/figuras", help="Carpeta de salida (por defecto docs/figuras)")
    args = ap.parse_args(argv)
    for p in build_pipeline_figure(Path(args.out)):
        print(p)


if __name__ == "__main__":
    main()
