# Prompt — Démo filmée du portail : profil `referent`

Prompt réutilisable pour produire une **vidéo de démonstration** du portail de
restitution vu par un **référent pédagogique**. Dérivé de
[qa_docker_demo_prompt.md](qa_docker_demo_prompt.md), dont il garde le principe
directeur : rien n'est codé en dur, tout est découvert depuis l'environnement.

---

Tu es un ingénieur QA qui réalise une démo filmée du portail de restitution de ce
projet, du point de vue d'un **référent pédagogique**.

## Principe directeur : ZÉRO valeur codée en dur

Tu ne présupposes AUCUN port, domaine, identifiant ni mot de passe. Tu les
découvres :

- **URL** : `DECROCHAGE_DOMAIN` dans `.env` (défaut `localhost`), servie en HTTPS
  par le service de reverse-proxy trouvé dans `docker compose ps`.
- **Comptes** : `docker compose exec api decrochage portal-user-list` → prends le
  premier compte dont le `role` vaut `referent` et note son `scope`.
- **Mot de passe** : variable d'environnement `PORTAL_DEMO_PASSWORD`. Si elle est
  absente, **demande-le à l'opérateur et n'écris jamais sa valeur** dans un
  fichier, un log ou un nom de chapitre.

Si aucun compte `referent` n'existe, arrête-toi et indique la commande de
création (`portal-user-add <identifiant> --role referent --filieres "<filière>"`),
sans inventer d'identifiants.

## Objectif unique : produire une vidéo

Le livrable est **la vidéo** (`.webm`), rien d'autre. Ne génère aucun rapport.

## Préparation

1. `docker compose --profile run up -d --build` puis attends `healthy`.
2. Vérifie que le portail est monté : `curl -sk -o /dev/null -w "%{http_code}"
   https://<domaine>/portal/login` doit renvoyer `200`. Un `404` signifie
   `DECROCHAGE_PORTAL_ENABLED=false` ou une image qui ne contient pas `portal/` :
   signale-le et arrête.
3. Vérifie qu'il y a des données à montrer : `docker compose exec api decrochage
   portal-user-list` pour les comptes, et une requête SQL de comptage sur
   `gold_prediction`. Une base vide donnerait une démo d'écrans vides — dis-le
   plutôt que de filmer.
4. `playwright-cli open https://<domaine>/portal/login --browser=chrome --headed`
5. **Certificat auto-signé** : en local, Caddy signe avec une autorité locale.
   Chrome affiche « Votre connexion n'est pas privée ». C'est le comportement
   attendu : clique « Paramètres avancés » puis « Continuer vers le site ». Filme
   ce passage, il fait partie de la démonstration.
6. `playwright-cli video-start reports/screenshots/portail/qa-portail-referent.webm`
7. `playwright-cli video-show-actions --duration=600 --position=top-right`

## Règles de navigation (OBLIGATOIRE à chaque interaction)

- `playwright-cli mousemove [x] [y]` → puis `sleep 1`
- Ensuite seulement : click / type / scroll
- Entre chaque chapitre : `playwright-cli video-chapter "[Titre]"
  --description="..." --duration=3000`

## Chapitres à couvrir

1. **« Le portail exige une authentification »**
   → Avant de te connecter, va sur `/portal/cohorte` : tu es redirigé vers la
     connexion. Montre l'URL de redirection avec son paramètre `next`.
   → Reviens au formulaire, souligne la mention « identifiant du SI, pas une
     adresse de courriel ».

2. **« Connexion et périmètre »**
   → `mousemove` + saisie de l'identifiant, puis du mot de passe (masqué à
     l'écran par le navigateur — vérifie-le à l'image).
   → Après connexion, montre l'en-tête : rôle et **périmètre de filières**.
     Le référent atterrit sur la cohorte, pas sur une page d'accueil générique.

3. **« Cohorte priorisée »**
   → Bandeau de contexte : lot, date, version de modèle, seuil actif, nombre
     d'alertes. Insiste : aucun affichage sans horodatage.
   → Le tableau est trié par probabilité décroissante — fais défiler pour le
     montrer.
   → Les pseudonymes sont abrégés : **aucun nom, aucun identifiant en clair**.
   → Filtres : coche « alertes seules », change de filière si le périmètre en
     autorise plusieurs, puis règle le **curseur de capacité** et montre la ligne
     de démarcation du top-K.
   → Bandeau d'avertissement non masquable : lis-le à l'écran.

4. **« Fiche de risque — pourquoi ce signalement »**
   → Ouvre le premier dossier. Montre : probabilité, alerte, seuil, modèle, lot.
   → **Facteurs aggravants et protecteurs** en libellés métier, avec le sens de
     l'effet et la valeur observée.
   → Arrête-toi sur la **mention méthodologique** : les contributions donnent un
     ordre et un sens, jamais une part de responsabilité.
   → Section « Variables observées » : uniquement les variables du modèle.
   → Le **motif de consultation** est obligatoire : choisis-en un dans la liste
     fermée et explique qu'il part dans le journal d'audit.

5. **« Cloisonnement — ce que le référent ne peut pas faire »**
   → Forge l'URL d'un pseudonyme hors périmètre (64 caractères hexadécimaux
     inexistants) : la réponse est **404, pas 403**. Explique la nuance : un 403
     confirmerait l'existence du dossier.
   → Va sur `/portal/conformite` : **403**, la vue est réservée au DPO.

6. **« Export vers le SI »**
   → Déclenche l'export CSV, ouvre le fichier téléchargé.
   → Montre l'en-tête de finalité, la mention « ne pas rediffuser », et que les
     colonnes s'arrêtent à `pseudo_id, rang, proba_abandon, alerte, filiere,
     batch_id, model_version, threshold, generated_at`.
   → Souligne que le nombre de lignes correspond au **périmètre**, pas à la
     cohorte entière.

7. **« Limites du modèle »**
   → `/portal/a-propos` : usage prévu, usages exclus, métriques, variables
     écartées et pourquoi (fuite de données, fuite temporelle, leurres).
   → Insiste sur la mention « performances établies sur données synthétiques ».

8. **« Console propre »**
   → `playwright-cli console` : relève à l'écran l'absence d'erreur et de
     ressource distante bloquée par la CSP.

9. **« Clôture »**
   → Déconnexion, retour au formulaire.
   → `playwright-cli video-stop` puis `playwright-cli close`.

## Nettoyage

Ne fais PAS `docker compose down` sans confirmation : la stack peut devoir rester
en ligne. Propose-le à la fin.
