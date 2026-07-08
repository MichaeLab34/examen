"""Package utilitaire du cas d'usage « détection précoce du décrochage étudiant ».

Regroupe le code réutilisable et reproductible hors notebook :
- `preprocessing` : parsing des données brutes (%, virgules FR, « km », dates
  multi-formats), normalisation des catégories, dédoublonnage.
- `features` : feature engineering métier + définition stricte du périmètre de
  scoring (colonnes exclues pour cause de fuite de données / fuite temporelle /
  leurres).
- `serving` : contrat d'entrée/sortie et fonction `predict_proba_abandon` pour
  un service de prédiction (compétence C6).

Le notebook de restitution reste la source de vérité de la démarche ; ce package
en isole les fonctions déterministes pour garantir la reproductibilité et pour
que le modèle sérialisé (joblib) soit rechargeable en dehors du notebook (les
classes/fonctions ne vivent pas dans `__main__`).
"""

from __future__ import annotations

__all__ = ["preprocessing", "features", "serving"]
