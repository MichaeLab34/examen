# Prompt — Démo filmée du portail : profil `auditeur` (DPO)

Prompt réutilisable pour produire une **vidéo de démonstration** du portail vu
par un **délégué à la protection des données**. Dérivé de
[qa_docker_demo_prompt.md](qa_docker_demo_prompt.md), dont il garde le principe
directeur : rien n'est codé en dur, tout est découvert depuis l'environnement.

---

Tu es un ingénieur QA qui réalise une démo filmée du portail de restitution de ce
projet, du point de vue d'un **DPO**. Le fil de cette démo n'est pas ce que le
DPO peut faire, mais ce qu'il peut **prouver sans accéder aux données**.

## Principe directeur : ZÉRO valeur codée en dur

- **URL** : `DECROCHAGE_DOMAIN` dans `.env` (défaut `localhost`), servie en HTTPS
  par le reverse-proxy trouvé dans `docker compose ps`.
- **Compte** : `docker compose exec api decrochage portal-user-list` → premier
  compte de rôle `auditeur`.
- **Mot de passe** : variable `PORTAL_DEMO_PASSWORD`. Absente, demande-la à
  l'opérateur et **n'écris jamais sa valeur** où que ce soit.

Si aucun compte `auditeur` n'existe, arrête-toi et indique
`portal-user-add <identifiant> --role auditeur`.

## Objectif unique : produire une vidéo

Le livrable est **la vidéo** (`.webm`), rien d'autre. Ne génère aucun rapport.

## Préparation

1. `docker compose --profile run up -d --build` puis attends `healthy`.
2. `curl -sk -o /dev/null -w "%{http_code}" https://<domaine>/portal/login` → `200`.
3. **Produis de la matière d'audit avant de filmer.** La vue de conformité est
   vide si personne n'a rien consulté. Connecte-toi d'abord avec un compte
   `referent`, ouvre une fiche et lance un export, puis déconnecte-toi : le
   journal aura des lignes réelles à montrer. Cette étape n'a pas besoin d'être
   filmée.
4. `playwright-cli open https://<domaine>/portal/login --browser=chrome --headed`
5. **Certificat auto-signé** : « Paramètres avancés » → « Continuer vers le
   site ». Attendu en local, filme-le.
6. `playwright-cli video-start reports/screenshots/portail/qa-portail-auditeur.webm`
7. `playwright-cli video-show-actions --duration=600 --position=top-right`

## Règles de navigation (OBLIGATOIRE à chaque interaction)

- `playwright-cli mousemove [x] [y]` → puis `sleep 1`
- Ensuite seulement : click / type / scroll
- Entre chaque chapitre : `playwright-cli video-chapter "[Titre]"
  --description="..." --duration=3000`

## Chapitres à couvrir

1. **« Contrôler sans accéder »**
   → Connecte-toi. Le DPO atterrit directement sur la **vue de conformité**.
   → Annonce le fil : tout ce qui suit se fait **sans jamais voir un score
     individuel ni un nom d'étudiant**.

2. **« Journal des consultations »**
   → Montre les événements : action, acteur **nominatif**, type de cible, motif,
     horodatage.
   → Distingue les actions de traitement (ingestion, persistance des scores) des
     actions humaines (`portal_login`, `portal_view_cohort`,
     `portal_view_student`, `portal_export`).
   → Arrête-toi sur une ligne `portal_view_student` : la cible est un
     **pseudonyme**, jamais un identifiant étudiant, et le **motif** est celui
     que le référent a choisi dans une liste fermée.
   → Explique ce que cela permet : répondre à « qui a consulté ce dossier, quand
     et pourquoi », sans stocker un identifiant en clair.

3. **« Rétention et échéances »**
   → Tableau des lots : identifiant, source, volumétries Bronze / Silver / Gold,
     date d'expiration, jours restants.
   → Explique la mécanique : chaque lot porte son échéance ; `purge-expired`
     supprime en cascade les lots échus et journalise l'opération.
   → Si un lot échu apparaît en évidence, montre-le : c'est le signal d'une purge
     à passer.

4. **« Modèle et surveillance »**
   → Encart modèle : version active, seuil, date d'entraînement.
   → Statut de dérive et compteurs `watch` / `alert` s'ils sont présents.
   → Le lien avec l'audit : on peut rattacher une décision à la **version de
     modèle et au seuil en vigueur au moment où elle a été prise**.

5. **« Ce que le DPO ne peut pas faire »** — le cœur de la démonstration
   → `/portal/cohorte` : **403**.
   → `/portal/pilotage` : **403**.
   → Forge l'URL d'une fiche individuelle : **403** également — le contrôle porte
     sur la route, pas sur l'existence du dossier.
   → Utilise la recherche du navigateur sur la page de conformité pour montrer
     qu'aucune probabilité individuelle n'y figure.
   → Formule-le clairement : le rôle qui contrôle la conformité est celui qui a
     le moins d'accès aux données. C'est la séparation des pouvoirs, appliquée.

6. **« Aucun identifiant en clair »**
   → Sur les pages visitées, cherche les motifs d'identifiants du jeu de données
     (`ETU-` suivi de cinq chiffres, `DOS-` suivi de quatre) : **zéro
     occurrence**.
   → Rappelle la conséquence : une compromission du portail n'expose aucune
     identité étudiante, faute de table de correspondance.

7. **« Limites assumées »**
   → `/portal/a-propos` : usages exclus, variables écartées, et la mention
     « performances établies sur données synthétiques ».

8. **« Console propre »**
   → `playwright-cli console` : aucune erreur, aucune ressource distante.

9. **« Clôture »**
   → Déconnexion.
   → `playwright-cli video-stop` puis `playwright-cli close`.

## Nettoyage

Ne fais PAS `docker compose down` sans confirmation. Propose-le à la fin.
