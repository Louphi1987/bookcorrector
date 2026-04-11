# Karamaz Correcteur

Application web de correction de manuscrits en francais, prevue pour un deploiement separe sur Render sous un sous-domaine du type `correcteur.karamaz.eu`.

## Positionnement

- service annexe, distinct du site principal ;
- deploiement gratuit possible sur Render Free ;
- fonctionnement stateless pour rester compatible avec un disque ephemere ;
- message UX assume: premier chargement parfois plus lent si le service etait en veille.

## Fonctionnalites

- glisser-deposer ou import manuel d'un manuscrit ;
- prise en charge de `.txt`, `.md`, `.docx` et `.odt` ;
- analyse hors API, basee sur des regles locales portables ;
- comparatif visuel avant/apres dans l'interface ;
- activation ou desactivation de chaque correction ;
- export en `.docx` avec version corrigee, surlignage des changements et tableau de suggestions.

## Stack

- Python 3.12
- Flask
- python-docx
- HTML/CSS/JavaScript vanille

## Lancement local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Puis ouvrir `http://127.0.0.1:5000`.

## Deploiement Render

Le projet inclut un fichier `render.yaml`. Il suffit de :

1. creer un depot GitHub pour ce projet ;
2. pousser le code ;
3. creer un nouveau service Web sur Render a partir du repo ;
4. verifier que le plan gratuit est choisi ;
5. associer le sous-domaine `correcteur.karamaz.eu`.

Render attend qu'un web service ecoute sur `0.0.0.0:$PORT`, ce qui est deja configure dans `render.yaml`.

## Limites volontaires de la V1

- pas de dependance a macOS ;
- pas de service externe payant ;
- moteur de correction base sur des regles et suggestions prudentes ;
- pas de suivi des modifications Word natif, mais un export `.docx` lisible avec changements surlignes et rapport detaille.
