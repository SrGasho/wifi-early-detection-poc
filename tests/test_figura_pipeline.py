import pathlib

import pytest

from scripts import figura_pipeline as FP

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_every_module_in_the_figure_exists_in_the_code():
    """Si un modulo se renombra o se borra, la figura no puede seguir mencionandolo."""
    missing = [m for m in FP.all_modules()
               if not ((ROOT / "src" / f"{m}.py").exists() or (ROOT / "scripts" / f"{m}.py").exists())]
    assert missing == []


def test_phases_are_the_six_of_crisp_dm_in_order():
    assert [p.name for p in FP.PHASES] == [
        "Comprensión del negocio", "Comprensión de datos", "Preparación",
        "Modelado", "Evaluación", "Despliegue",
    ]


def test_paper_module_table_lists_the_same_modules():
    """La tabla de modulos del paper y la figura deben coincidir."""
    tex = (ROOT / "docs" / "paper" / "paper.tex").read_text(encoding="utf-8")
    table = tex[tex.index(r"\label{tab:modulos}"):]
    table = table[:table.index(r"\end{table*}")]
    in_paper = {m for m in FP.all_modules() if r"\path{" + m + "}" in table}
    assert in_paper == set(FP.all_modules())


def test_build_writes_vector_and_raster_figures(tmp_path):
    paths = FP.build_pipeline_figure(tmp_path)
    assert {p.suffix for p in paths} == {".pdf", ".png"}
    assert all(p.exists() and p.stat().st_size > 1000 for p in paths)
    assert all(p.stem == "pipeline-crisp-dm" for p in paths)


def test_build_does_not_write_outside_the_output_dir(tmp_path):
    def snapshot():
        return {p for d in ("docs", "scripts") for p in (ROOT / d).rglob("*")
                if p.is_file() and "__pycache__" not in p.parts}

    before = snapshot()
    FP.build_pipeline_figure(tmp_path)
    assert snapshot() == before


@pytest.mark.parametrize("name", ["experiment"])
def test_cross_cutting_module_is_declared(name):
    assert name in FP.CROSS_CUTTING
