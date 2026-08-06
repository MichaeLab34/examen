# Prompt — Démo filmée du portail : profil `pilote`

Prompt réutilisable pour produire une **vidéo de démonstration** du portail vu
par un **responsable de la réussite étudiante**. Dérivé de
[qa_docker_demo_prompt.md](qa_docker_demo_prompt.md), dont il garde le principe
directeur : rien n'est codé en dur, tout est découvert depuis l'environnement.

---

Tu es un ingénieur QA qui réalise une démo filmée du portail de restitution de ce
projet, du point de vue d'un **pilote de la réussite étudiante**.

## Principe directeur : ZÉRO valeur codée en dur

- **URL** : `DECROCHAGE_DOMAIN` dans `.env` (défaut `localhost`), servie en HTTPS
  par le reverse-proxy trouvé dans `docker compose ps`.
- **Compte** : `docker compose exec api decrochage portal-user-list` → premier
  compte de rôle `pilote` ; son `scope` doit être `global`.
- **Mot de passe** : variable `PORTAL_DEMO_PASSWORD`. Absente, demande-la à
  l'opérateur et **n'écris jamais sa valeur** dans un fichier, un log ou un
  titre de chapitre.

Si aucun compte `pilote` n'existe, arrête-toi et indique
`portal-user-add <identifiant> --role pilote`, sans inventer d'identifiants.

## Objectif unique : produire une vidéo

Le livrable est **la vidéo** (`.webm`), rien d'autre. Ne génère aucun rapport.

## Préparation

1. `docker compose --profile run up -d --build` puis attends `healthy`.
2. `curl -sk -o /dev/null -w "%{http_code}" https://<domaine>/portal/login` → `200`
   attendu. Un `404` signifie portail désactivé ou image sans `portal/`.
3. Vérifie qu'un lot est chargé et scoré : une vue agrégée sur base vide n'a
   rien à montrer. Dis-le plutôt que de filmer des tableaux vides.
4. `playwright-cli open https://<domaine>/portal/login --browser=chrome --headed`
5. **Certificat auto-signé** : « Paramètres avancés » → « Continuer vers le
   site ». Comportement attendu en local, filme-le.
6. `playwright-cli video-start reports/screenshots/portail/qa-portail-pilote.webm`
7. `playwright-cli video-show-actions --duration=600 --position=top-right`

## Règles de navigation (OBLIGATOIRE à chaque interaction)

- `playwright-cli mousemove [x] [y]` → puis `sleep 1`
- Ensuite seulement : click / type / scroll
- Entre chaque chapitre : `playwright-cli video-chapter "[Titre]"
  --description="..." --duration=3000`

## Chapitres à couvrir

1. **« Un rôle, une porte d'entrée »**
   → Connecte-toi. Le pilote n'atterrit pas sur la cohorte mais sur la **vue de
     pilotage** : la redirection dépend du rôle, relu en base à chaque requête.
   → Montre l'en-tête : rôle et périmètre global.

2. **« Indicateurs par filière »**
   → Bandeau de contexte : lot, date, modèle, seuil en vigueur.
   → Tableau : effectif, alertes, taux d'alerte, probabilité médiane, **décile
     supérieur**.
   → Explique pourquoi il n'y a **pas de maximum** : un maximum est le score d'un
     étudiant précis, ce qui viderait de son sens une vue agrégée.
   → S'il est affiché, montre le message sur les **filières de faible effectif**
     regroupées : en dessous de cinq étudiants, un agrégat désigne des individus.

3. **« Distribution des risques »**
   → Histogramme rendu en **SVG côté serveur** : aucune bibliothèque graphique
     cliente, aucune ressource distante — c'est ce qui permet une CSP stricte.
   → `mousemove` le long des barres, puis montre le tableau d'effectifs par
     tranche qui le double pour l'accessibilité.

4. **« Simulateur de seuil »**
   → Relève le seuil affiché **en vigueur**, puis saisis une valeur différente et
     lance la simulation.
   → Montre que le **volume d'alertes induit** change.
   → Point capital : le seuil du modèle en production **n'est pas modifié**.
     Prouve-le à l'image — le bandeau de contexte affiche toujours le seuil réel.
     Fais deux simulations opposées (seuil bas, seuil haut) pour rendre visible
     l'arbitrage rappel / charge de travail.

5. **« Avertissement d'équité »**
   → Arrête-toi sur l'encart : un écart de taux d'alerte entre filières peut
     traduire un biais indirect et non un écart réel de risque. Un arbitrage de
     moyens s'appuie sur l'audit par sous-groupes, pas sur ce tableau seul.

6. **« Cloisonnement — ce que le pilote ne voit pas »**
   → `/portal/cohorte` : **403**. Le pilote arbitre des moyens, il n'a pas à
     ouvrir de dossiers individuels.
   → `/portal/conformite` : **403**, réservé au DPO.
   → Vérifie qu'aucun lien vers une fiche individuelle n'existe sur ses écrans.

7. **« Export global »**
   → Déclenche l'export : le pilote exporte sur **tout** le périmètre, là où le
     référent est limité à ses filières — la différence est portée par le filtre
     SQL, pas par le contrôle de rôle.
   → Montre les colonnes fermées et l'en-tête de finalité.
   → Si le plafond anti-exfiltration est atteint, montre le message : c'est un
     garde-fou, pas un bug.

8. **« Console propre »**
   → `playwright-cli console` : aucune erreur, aucune ressource distante bloquée.

9. **« Clôture »**
   → Déconnexion.
   → `playwright-cli video-stop` puis `playwright-cli close`.

## Nettoyage

Ne fais PAS `docker compose down` sans confirmation. Propose-le à la fin.
