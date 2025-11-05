# 📂 Utiliser des dossiers /input et /output avec Docker

## Structure recommandée

Si vous préférez utiliser des dossiers `/input` et `/output` au lieu de `ebooks/` et `audiobooks/`, voici comment faire :

### 1. Créer la structure de dossiers

```bash
cd ebook2audiobook
mkdir -p input output tmp models voices
```

Votre structure sera :
```
ebook2audiobook/
├── input/              ← Placez vos ebooks ici
├── output/             ← Les audiobooks seront générés ici
├── tmp/                ← Checkpoints et fichiers temporaires
├── models/             ← Modèles TTS (téléchargés automatiquement)
├── voices/             ← Vos voix personnalisées (optionnel)
└── docker-compose.custom.yml
```

### 2. Utiliser le docker-compose personnalisé

J'ai créé un fichier `docker-compose.custom.yml` qui mappe automatiquement ces dossiers.

**Démarrer en mode GUI :**
```bash
docker-compose -f docker-compose.custom.yml up
```

**Mode headless (CLI) :**
```bash
# Placer votre ebook dans input/
cp mon_livre.epub input/

# Lancer la conversion
docker-compose -f docker-compose.custom.yml run --rm ebook2audiobook \
  --headless \
  --ebook "ebooks/mon_livre.epub" \
  --language fr \
  --session livre-123

# Le fichier audio sera dans output/
ls -lh output/
```

### 3. Avec checkpoint et reprise

**Première conversion (interrompue) :**
```bash
# Placer le livre dans input/
cp long_book.epub input/

# Démarrer la conversion
docker-compose -f docker-compose.custom.yml run --rm ebook2audiobook \
  --headless \
  --ebook "ebooks/long_book.epub" \
  --language fr \
  --session long-book-123

# Ctrl+C pour interrompre
```

**Reprendre la conversion :**
```bash
# Même commande - le checkpoint sera détecté automatiquement
docker-compose -f docker-compose.custom.yml run --rm ebook2audiobook \
  --headless \
  --ebook "ebooks/long_book.epub" \
  --language fr \
  --session long-book-123

# Affiche :
# ============================================================
# ✓ Found existing checkpoint!
#   Stage: audio_converted
#   Time: 2025-11-05T18:30:45
#   Resuming from last checkpoint...
# ============================================================

# Le fichier final sera dans output/
```

### 4. Vérifier les checkpoints

Les checkpoints sont sauvegardés dans `tmp/` :

```bash
# Voir tous les checkpoints
find tmp/ -name "checkpoint.json"

# Voir le contenu d'un checkpoint
cat tmp/proc-livre-123/*/checkpoint.json | jq .
```

## Mapping des volumes

Le fichier `docker-compose.custom.yml` mappe les dossiers comme suit :

| Hôte | Conteneur | Usage |
|------|-----------|-------|
| `./input/` | `/app/ebooks/` | Ebooks sources |
| `./output/` | `/app/audiobooks/cli/` | Audiobooks générés |
| `./tmp/` | `/app/tmp/` | Checkpoints + temporaires |
| `./models/` | `/app/models/` | Modèles TTS téléchargés |
| `./voices/` | `/app/voices/` | Voix personnalisées |

## Workflow complet

### Exemple : Convertir plusieurs livres avec reprise

```bash
# 1. Créer la structure
mkdir -p input output tmp models voices

# 2. Copier vos ebooks
cp ~/mes_livres/*.epub input/

# 3. Convertir chaque livre (avec session ID unique)
for book in input/*.epub; do
  FILENAME=$(basename "$book" .epub)

  echo "Converting: $FILENAME"

  docker-compose -f docker-compose.custom.yml run --rm ebook2audiobook \
    --headless \
    --ebook "ebooks/$FILENAME.epub" \
    --language fr \
    --session "$FILENAME" \
    --tts_engine XTTSv2

  # Si interrompu, le script reprendra au prochain lancement
done

# 4. Vérifier les résultats
ls -lh output/
```

### Exemple : Mode GUI avec input/output

```bash
# 1. Démarrer l'interface web
docker-compose -f docker-compose.custom.yml up

# 2. Ouvrir http://localhost:7860

# 3. Dans l'interface :
#    - Uploader un ebook
#    - Configurer les paramètres
#    - Lancer la conversion
#    - Les audiobooks apparaîtront dans output/

# 4. Si vous fermez le navigateur, les checkpoints sont sauvegardés
#    Relancer et la session reprendra automatiquement
```

## Avantages de cette structure

✅ **Clarté** : input/ et output/ sont explicites
✅ **Portabilité** : Facile à comprendre pour les nouveaux utilisateurs
✅ **Séparation** : Données sources séparées des résultats
✅ **Checkpoints persistants** : tmp/ conserve tous les états
✅ **Cache de modèles** : models/ évite de retélécharger

## Nettoyage

```bash
# Supprimer les fichiers temporaires (garde les checkpoints actifs)
docker-compose -f docker-compose.custom.yml run --rm ebook2audiobook \
  find tmp/ -name "*.flac" -delete

# Supprimer tous les checkpoints et temporaires
rm -rf tmp/*

# Nettoyer les anciens audiobooks
rm -rf output/*.m4b

# Tout nettoyer (attention : supprime les checkpoints !)
rm -rf tmp/* output/*
```

## Permissions

Si vous avez des problèmes de permissions :

```bash
# Donner les permissions à Docker
chmod -R 777 input/ output/ tmp/ models/ voices/

# Ou utiliser votre user ID
docker-compose -f docker-compose.custom.yml run \
  --user $(id -u):$(id -g) \
  --rm ebook2audiobook \
  --headless --ebook "ebooks/livre.epub" --language fr
```

## Comparaison des structures

### Structure par défaut (docker-compose.yml)
```
ebook2audiobook/
├── ebooks/         ← input
├── audiobooks/
│   ├── cli/       ← output CLI
│   └── gui/       ← output GUI
└── tmp/           ← checkpoints
```

### Structure personnalisée (docker-compose.custom.yml)
```
ebook2audiobook/
├── input/         ← ebooks sources
├── output/        ← tous les audiobooks
├── tmp/           ← checkpoints
├── models/        ← cache TTS
└── voices/        ← voix custom
```

Choisissez celle qui vous convient ! Les deux fonctionnent parfaitement avec les checkpoints. 🎉
