import json
import re
from pathlib import Path


def test_notebook_outputs_do_not_expose_clear_student_ids() -> None:
    notebook = json.loads(Path("notebooks/decrochage_etudiant.ipynb").read_text(encoding="utf-8"))
    outputs_text = json.dumps(
        [cell.get("outputs", []) for cell in notebook["cells"]],
        ensure_ascii=False,
    )

    assert not re.search(r"ETU-\d{5}", outputs_text)


def test_notebook_models_use_gold_dataset_as_source() -> None:
    notebook = json.loads(Path("notebooks/decrochage_etudiant.ipynb").read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])

    assert "gold_dataset, feature_cols = T.build_gold_dataset(" in source
    assert "T.build_gold_dataset(\n    silver_dataset," in source
    assert "X = gold_dataset[feature_cols].copy()" in source
    assert "y_clf = gold_dataset[F.TARGET_CLF].astype(int)" in source
    assert "y_reg = gold_dataset[F.TARGET_REG].astype(float)" in source
    assert "serving.predict_from_gold_dataset(modele_charge, X_demo)" in source

    assert "df = silver_dataset" not in source
    assert "T.build_gold_dataset(\n    df," not in source
    assert "X = df[feature_cols]" not in source
    assert "X = df[feature_cols].copy()" not in source
    assert "y_clf = df[F.TARGET_CLF]" not in source
    assert "y_reg = df[F.TARGET_REG]" not in source
    assert "gold_dataset = df[feature_cols + gold_label_cols].copy()" not in source


def test_notebook_does_not_preview_or_score_from_raw_students() -> None:
    notebook = json.loads(Path("notebooks/decrochage_etudiant.ipynb").read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])

    assert "df_raw" not in source
    assert "public_preview" not in source
    assert "echantillon_brut" not in source
    assert "predict_proba_abandon(modele_charge" not in source
