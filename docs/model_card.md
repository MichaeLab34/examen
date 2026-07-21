# Model Card

## Model Details

- Project: early detection of student dropout risk in L1.
- Primary task: binary classification of `abandon`.
- Secondary task in the notebook: regression of `moyenne_finale`.
- Model family: regularized logistic regression in an sklearn pipeline.
- Package artifact: `ModelBundle` with preprocessing, feature list, threshold,
  catalogue and metadata.

## Intended Use

The model helps student-success teams prioritize human outreach at mid-S1. It
must be used as decision support only. It must not automatically exclude,
sanction, orient or label a student without human review.

## Out-of-Scope Use

- Automated individual decisions.
- Use outside L1 without revalidation.
- Use after S1 if the feature availability window changes.
- Use on real student data without DPO review and stakeholder information.
- Export or publish row-level data without an anonymization study.

## Evaluation

The notebook reports ROC AUC, precision, recall, F1, confusion matrix and
business-threshold analysis. The package training path selects the threshold on
validation data and reserves test data for final reporting. Training metadata
also records the maximum recall gap observed across monitored `sexe` and
`boursier` subgroups.

## Model Lifecycle

New bundles enter MLflow as `candidate`. Promotion to `production` is blocked
unless test AUC is at least 0.85, recall is at least 0.90 and does not regress
against the current production model, and the monitored subgroup recall gap is
at most 10 points. Passing the technical gate is insufficient: a human reviewer
must still approve the model. The previous version remains reachable for
rollback through the `archived` alias.

## Limitations

The provided data is synthetic and intentionally simplified. Performance must be
revalidated on real cohorts, with subgroup analysis and an A/B test of the
support process before production deployment.

## Ethical Considerations

Sensitive or proxy variables include `sexe`, `boursier` and
`etablissement_origine`. Monitor subgroup recall and alert rates. Keep the final
decision human, explainable and reversible. Direct identifiers are not model
features; they are kept raw only in restricted Bronze and HMAC-pseudonymized
from Silver onward.
