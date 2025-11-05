# 🐳 Checkpoint & Resume avec Docker

## ✅ Oui, ça fonctionne avec Docker !

La fonctionnalité de checkpoint fonctionne **parfaitement avec Docker** grâce au montage de volumes dans le `docker-compose.yml`.

## Comment ça marche

### Persistance des données

Dans `docker-compose.yml`, ligne 31 :
```yaml
volumes:
  - ./:/app  # Monte le répertoire local dans le conteneur
```

Cela signifie que :
- ✅ Les checkpoints sont sauvegardés dans `./tmp/` sur votre **machine hôte**
- ✅ Les fichiers audio générés restent sur votre **disque local**
- ✅ Si le conteneur s'arrête, **toutes les données sont préservées**
- ✅ Vous pouvez redémarrer le conteneur et reprendre où vous étiez

### Structure des fichiers

Sur votre machine hôte :
```
ebook2audiobook/
├── tmp/
│   └── proc-{session-id}/
│       └── {ebook-hash}/
│           ├── checkpoint.json          ← Checkpoint sauvegardé ici
│           ├── __book.epub
│           └── chapters/
│               ├── chapter_1.flac
│               ├── chapter_2.flac
│               └── sentences/
│                   ├── 1.flac
│                   ├── 2.flac
│                   └── ...
```

Même si le conteneur Docker est détruit, ces fichiers restent sur votre disque.

## Utilisation avec Docker Compose

### 1. Démarrer une conversion

**Mode GUI :**
```bash
docker-compose up
# Ouvrir http://localhost:7860 dans votre navigateur
```

**Mode Headless (CLI) :**
```bash
docker-compose run --rm ebook2audiobook \
  --headless \
  --ebook "ebooks/mon_livre.epub" \
  --language fr \
  --session ma-session-123
```

### 2. Arrêter le conteneur (interruption)

```bash
# Ctrl+C ou
docker-compose down
```

Les checkpoints et fichiers audio sont **automatiquement sauvegardés** sur votre machine hôte.

### 3. Reprendre la conversion

**Redémarrer avec le même session ID :**

```bash
docker-compose run --rm ebook2audiobook \
  --headless \
  --ebook "ebooks/mon_livre.epub" \
  --language fr \
  --session ma-session-123
```

Le système détecte automatiquement le checkpoint et reprend !

### 4. Forcer un redémarrage

```bash
docker-compose run --rm ebook2audiobook \
  --headless \
  --ebook "ebooks/mon_livre.epub" \
  --language fr \
  --session ma-session-123 \
  --force_restart
```

## Utilisation avec Docker Run

### Sans docker-compose

Si vous utilisez directement `docker run` :

```bash
# Première conversion
docker run --rm -it \
  -v $(pwd):/app \
  -p 7860:7860 \
  athomasson2/ebook2audiobook \
  --headless \
  --ebook "ebooks/mon_livre.epub" \
  --language fr \
  --session ma-session-123

# Reprendre après interruption (même commande)
docker run --rm -it \
  -v $(pwd):/app \
  -p 7860:7860 \
  athomasson2/ebook2audiobook \
  --headless \
  --ebook "ebooks/mon_livre.epub" \
  --language fr \
  --session ma-session-123
```

**⚠️ Important :** Le flag `-v $(pwd):/app` est **CRUCIAL** pour la persistance des checkpoints !

## Scénarios Docker

### Scénario 1 : Arrêt propre du conteneur
```bash
# Démarrer
docker-compose up
# Ctrl+C pour arrêter
docker-compose down

# Redémarrer - les checkpoints sont préservés
docker-compose up
```
✅ **Résultat :** Reprise automatique

### Scénario 2 : Crash du conteneur
```bash
# Le conteneur crash pendant la conversion
# Les checkpoints sont déjà sauvegardés sur l'hôte

# Redémarrer
docker-compose up
```
✅ **Résultat :** Reprise depuis le dernier checkpoint

### Scénario 3 : Suppression du conteneur
```bash
docker-compose down
docker rm ebook2audiobook

# Recréer le conteneur
docker-compose up
```
✅ **Résultat :** Les données persistent car elles sont sur l'hôte, pas dans le conteneur

### Scénario 4 : Rebuild de l'image
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up
```
✅ **Résultat :** Les checkpoints et données restent intacts

## Bonnes pratiques Docker

### 1. Toujours utiliser un Session ID
```bash
docker-compose run --rm ebook2audiobook \
  --headless \
  --ebook "livre.epub" \
  --language fr \
  --session "livre-1-$(date +%Y%m%d)"
```

### 2. Vérifier le montage du volume
```bash
docker-compose config | grep volumes -A 5
```

Doit afficher :
```yaml
volumes:
  - ./:/app
```

### 3. Inspecter les checkpoints depuis l'hôte
```bash
# Voir les sessions actives
ls -la tmp/

# Voir un checkpoint spécifique
cat tmp/proc-ma-session-123/*/checkpoint.json
```

### 4. Nettoyer après succès
Les checkpoints sont automatiquement supprimés quand la conversion réussit. Pour nettoyer manuellement :
```bash
# Supprimer les anciennes sessions
rm -rf tmp/proc-*

# Ou garder seulement les récentes (< 7 jours)
find tmp/ -name "proc-*" -mtime +7 -exec rm -rf {} \;
```

## Limitations et considérations

### ✅ Ce qui fonctionne
- Arrêt/redémarrage du conteneur
- Crash du conteneur
- Mise à jour de l'image Docker
- Conversion en mode GUI ou CLI
- Multiples livres en parallèle (sessions différentes)

### ⚠️ Ce qui ne fonctionne pas
- **Migration vers un autre ordinateur** : Les chemins absolus dans les checkpoints sont liés à votre machine
  - Solution : Transférer tout le dossier `tmp/` et garder la même structure

- **Changement de répertoire de montage** : Si vous changez le chemin du volume Docker
  - Solution : Utiliser toujours le même point de montage

### 🔒 Sécurité et permissions

Si vous avez des problèmes de permissions :

```bash
# Donner les permissions au conteneur Docker
chmod -R 777 tmp/ audiobooks/ ebooks/

# Ou utiliser le user ID de votre hôte
docker-compose run --user $(id -u):$(id -g) ebook2audiobook ...
```

## Exemples complets

### Exemple 1 : Conversion longue avec reprise

```bash
# Jour 1 : Démarrer la conversion d'un gros livre (2h de conversion)
docker-compose run --rm ebook2audiobook \
  --headless \
  --ebook "ebooks/war_and_peace.epub" \
  --language fr \
  --session war-peace-2025 \
  --tts_engine XTTSv2

# Après 1h, vous devez éteindre l'ordinateur
# Ctrl+C

# Jour 2 : Reprendre exactement où vous étiez
docker-compose run --rm ebook2audiobook \
  --headless \
  --ebook "ebooks/war_and_peace.epub" \
  --language fr \
  --session war-peace-2025 \
  --tts_engine XTTSv2

# Le système affiche :
# ============================================================
# ✓ Found existing checkpoint!
#   Stage: audio_converted
#   Time: 2025-11-05T18:30:45.123456
#   Resuming from last checkpoint...
# ============================================================
```

### Exemple 2 : Mode GUI avec sessions persistantes

```bash
# Démarrer l'interface web
docker-compose up

# Dans le navigateur :
# - Charger un livre
# - Commencer la conversion
# - Fermer le navigateur / arrêter le conteneur

# Plus tard, redémarrer
docker-compose up

# Les sessions précédentes sont toujours disponibles !
# Vous pouvez voir les checkpoints dans l'interface
```

### Exemple 3 : Batch processing avec reprise

```bash
# Convertir plusieurs livres
for book in ebooks/*.epub; do
  SESSION_ID=$(basename "$book" .epub)

  docker-compose run --rm ebook2audiobook \
    --headless \
    --ebook "$book" \
    --language fr \
    --session "$SESSION_ID"

  # Si un livre est interrompu, il reprendra automatiquement
  # au prochain lancement du script
done
```

## Monitoring et debugging

### Voir les checkpoints actifs
```bash
find tmp/ -name "checkpoint.json" -exec echo "==== {} ====" \; -exec cat {} \; -exec echo "" \;
```

### Taille des données
```bash
# Espace utilisé par les sessions
du -sh tmp/proc-*/

# Espace total
du -sh tmp/
```

### Logs Docker
```bash
# Voir les logs du conteneur
docker-compose logs -f

# Chercher les messages de checkpoint
docker-compose logs | grep -i checkpoint
```

## FAQ Docker

**Q: Les checkpoints fonctionnent-ils avec Docker sur Windows ?**
R: Oui ! Assurez-vous juste que le volume est bien monté (ligne 31 du docker-compose.yml).

**Q: Puis-je utiliser un volume Docker nommé au lieu de `./:/app` ?**
R: Oui, mais les checkpoints seront dans le volume Docker, pas directement accessibles depuis l'hôte.
```yaml
volumes:
  - ebook2audiobook-data:/app
```

**Q: Combien d'espace disque pour les checkpoints ?**
R: Très peu ! ~2-5 KB par checkpoint. Les fichiers audio prennent beaucoup plus de place.

**Q: Les checkpoints ralentissent-ils Docker ?**
R: Non, l'impact est négligeable (quelques millisecondes par sauvegarde).

**Q: Puis-je partager mes checkpoints avec un collègue ?**
R: Techniquement oui, mais il faut transférer :
- Le dossier `tmp/proc-{session-id}/`
- Le fichier ebook source
- Garder la même structure de dossiers

---

**Conclusion :** Les checkpoints fonctionnent **nativement et automatiquement** avec Docker grâce au montage de volumes. Aucune configuration supplémentaire n'est nécessaire ! 🎉
