# Guide de Refactorisation - app.py

Ce document explique comment intégrer proprement le module `distributed_manager.py` dans `app.py` pour découpler complètement le mode distribué.

---

## 🎯 Objectif

Remplacer les imports directs et la logique distribuée dans `app.py` par des appels au module unifié `distributed_manager.py`.

**Bénéfices**:
- ✅ Code principal ne dépend plus de redis/celery
- ✅ Mode distribué optionnel (pas d'erreur si dépendances manquantes)
- ✅ Gestion d'erreur robuste et messages clairs
- ✅ Plus facile à tester et maintenir

---

## 📝 Modifications à Apporter

### 1. Imports au début du fichier

**Fichier**: `app.py`

#### ❌ Avant (lignes 271-277)

```python
from lib.functions import SessionContext, convert_ebook_batch, convert_ebook, web_interface

# Plus loin dans le code...
if args.get('worker_mode', False):
    from lib.distributed.worker import start_worker  # Import direct
    worker_id = os.getenv('WORKER_ID', 'worker_1')
    gpu_id = os.getenv('CUDA_VISIBLE_DEVICES')
    start_worker(worker_id=worker_id, gpu_id=gpu_id)
```

#### ✅ Après

```python
from lib.functions import SessionContext, convert_ebook_batch, convert_ebook, web_interface

# Import du module distribué (seulement si disponible)
try:
    from lib.distributed_manager import (
        is_distributed_mode_available,
        initialize_coordinator,
        initialize_worker,
        DistributedModeError
    )
    DISTRIBUTED_MODE_AVAILABLE = True
except ImportError:
    DISTRIBUTED_MODE_AVAILABLE = False
    logger.warning("Distributed mode not available. Install: pip install -r requirements-distributed.txt")
```

**Explication**:
- Import dans un `try/except` pour gérer l'absence des dépendances
- Flag `DISTRIBUTED_MODE_AVAILABLE` pour décider si on ajoute les arguments CLI

---

### 2. Arguments CLI Conditionnels

**Fichier**: `app.py` (lignes 226-231)

#### ❌ Avant

```python
# Distributed mode options (toujours ajoutés)
distributed_group = parser.add_argument_group(
    '**** Distributed Mode Options (for multi-machine parallelism)',
    'Optional'
)
distributed_group.add_argument(options[27], action='store_true', ...)
distributed_group.add_argument(options[28], type=int, default=1, ...)
distributed_group.add_argument(options[29], type=str, ...)
distributed_group.add_argument(options[30], action='store_true', ...)
```

#### ✅ Après

```python
# Distributed mode options (seulement si disponible)
if DISTRIBUTED_MODE_AVAILABLE:
    distributed_group = parser.add_argument_group(
        '**** Distributed Mode Options (for multi-machine parallelism)',
        'Optional'
    )
    distributed_group.add_argument(
        '--distributed',
        action='store_true',
        help='(Optional) Enable distributed processing mode using Celery + Redis.'
    )
    distributed_group.add_argument(
        '--num_workers',
        type=int,
        default=1,
        help='(Optional) Number of workers for distributed processing. Default: 1.'
    )
    distributed_group.add_argument(
        '--redis_url',
        type=str,
        default='redis://localhost:6379/0',
        help='(Optional) Redis URL for distributed coordination.'
    )
    distributed_group.add_argument(
        '--worker_mode',
        action='store_true',
        help='(Optional) Start as a Celery worker (not coordinator).'
    )
else:
    # Informer l'utilisateur que le mode distribué n'est pas disponible
    logger.info(
        "Distributed mode arguments not available. "
        "Install with: pip install -r requirements-distributed.txt"
    )
```

**Explication**:
- Arguments ajoutés **seulement si** le mode distribué est disponible
- Message informatif si les dépendances manquent

---

### 3. Gestion du Mode Worker

**Fichier**: `app.py` (lignes 274-281)

#### ❌ Avant

```python
# Check if starting as worker
if args.get('worker_mode', False):
    print("Starting Celery worker...")
    from lib.distributed.worker import start_worker
    worker_id = os.getenv('WORKER_ID', 'worker_1')
    gpu_id = os.getenv('CUDA_VISIBLE_DEVICES')
    start_worker(worker_id=worker_id, gpu_id=gpu_id)
    return  # Exit after worker stops
```

#### ✅ Après

```python
# Check if starting as worker
if args.get('worker_mode', False):
    if not DISTRIBUTED_MODE_AVAILABLE:
        error = (
            "Cannot start worker: distributed mode dependencies not installed.\n"
            "Install with: pip install -r requirements-distributed.txt"
        )
        print(error)
        sys.exit(1)

    print("Starting Celery worker...")
    try:
        worker_id = os.getenv('WORKER_ID', 'worker_1')
        gpu_id = os.getenv('CUDA_VISIBLE_DEVICES')
        redis_url = args.get('redis_url') or os.getenv('REDIS_URL', 'redis://localhost:6379/0')

        # Utiliser le module unifié
        initialize_worker(
            worker_id=worker_id,
            gpu_id=gpu_id,
            redis_url=redis_url
        )
    except DistributedModeError as e:
        error = f"Failed to start worker: {e}"
        print(error)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nWorker stopped by user")
        sys.exit(0)

    return  # Exit after worker stops
```

**Explication**:
- Vérification précoce de `DISTRIBUTED_MODE_AVAILABLE`
- Utilisation de `initialize_worker()` du module unifié
- Gestion propre des erreurs avec `DistributedModeError`
- Support de Ctrl+C pour arrêter proprement

---

### 4. Mode Coordinator dans Headless

**Fichier**: `app.py` (après ligne 329)

#### Code à Ajouter

```python
# Dans la section headless (après ligne 329)
if args['ebook']:
    args['ebook'] = os.path.abspath(args['ebook'])
    if not os.path.exists(args['ebook']):
        error = f'Error: The provided --ebook "{args["ebook"]}" does not exist.'
        print(error)
        sys.exit(1)

    # ✅ NOUVEAU: Support du mode distribué
    if args.get('distributed', False):
        if not DISTRIBUTED_MODE_AVAILABLE:
            error = (
                "Cannot use distributed mode: dependencies not installed.\n"
                "Install with: pip install -r requirements-distributed.txt"
            )
            print(error)
            sys.exit(1)

        # Mode distribué
        try:
            from lib.distributed_manager import distribute_conversion

            # Initialiser coordinator
            initialize_coordinator(
                session_id=args['session'] or f"distributed_{uuid.uuid4().hex[:8]}",
                num_workers=args.get('num_workers', 1),
                redis_url=args.get('redis_url')
            )

            print(f"Distributed conversion with {args['num_workers']} workers...")

            # TODO: Adapter convert_ebook pour retourner chapitres
            # Pour l'instant, utiliser le mode normal
            progress_status, passed = convert_ebook(args, ctx)

            # Future implémentation:
            # chapters = extract_chapters_from_ebook(args['ebook'])
            # tts_config = build_tts_config(args)
            # result = distribute_conversion(
            #     chapters=chapters,
            #     tts_config=tts_config,
            #     output_path=output_path,
            #     resume=args.get('force_restart') is not True
            # )

        except DistributedModeError as e:
            error = f'Distributed conversion failed: {e}'
            print(error)
            sys.exit(1)
    else:
        # Mode normal (non distribué)
        progress_status, passed = convert_ebook(args, ctx)

    if passed is False:
        error = f'Conversion failed: {progress_status}'
        print(error)
        sys.exit(1)
```

**Explication**:
- Vérification de `args.get('distributed')` pour activer le mode
- Validation des dépendances avant de commencer
- Utilisation du module unifié
- TODO pour intégration complète (nécessite refactoring de `convert_ebook`)

---

## 🔧 Intégration Complète dans functions.py

Pour une intégration complète, il faut aussi adapter `lib/functions.py` pour supporter le mode distribué.

**Fichier**: `lib/functions.py`

### Nouvelle Fonction à Ajouter

```python
def convert_ebook_distributed(args, ctx):
    """
    Convertit un ebook en audiobook en mode distribué.

    Cette fonction:
    1. Extrait les chapitres de l'ebook
    2. Prépare la configuration TTS
    3. Distribue aux workers via DistributedManager
    4. Combine les résultats
    5. Génère le fichier final

    Args:
        args: Arguments de conversion (dict)
        ctx: SessionContext

    Returns:
        (progress_status, passed): Tuple (message, bool)
    """
    from lib.distributed_manager import (
        get_distributed_manager,
        distribute_conversion,
        DistributedModeError
    )

    session = ctx.get_session(args['session'])

    try:
        # 1. Extraire chapitres (réutiliser code existant)
        print("Extracting chapters from ebook...")
        chapters = extract_chapters_from_ebook(
            ebook_path=args['ebook'],
            language=args['language']
        )

        if not chapters:
            return ("No chapters found in ebook", False)

        print(f"Found {len(chapters)} chapters")

        # 2. Préparer configuration TTS
        tts_config = {
            'model_name': args.get('tts_engine', 'xtts'),
            'voice_name': args.get('voice'),
            'language': args['language'],
            'device': args.get('device', 'cuda'),
            'custom_model': args.get('custom_model'),
            'temperature': args.get('temperature'),
            'speed': args.get('speed'),
            # ... autres paramètres TTS
        }

        # 3. Préparer chemin de sortie
        output_filename = f"{session['filename_noext']}.{args['output_format']}"
        output_path = os.path.join(args['audiobooks_dir'], output_filename)

        # 4. Distribuer conversion
        print(f"Distributing to {args.get('num_workers', 1)} workers...")

        final_path = distribute_conversion(
            chapters=chapters,
            tts_config=tts_config,
            output_path=output_path,
            resume=not args.get('force_restart', False)
        )

        # 5. Ajouter métadonnées (réutiliser code existant)
        print("Adding metadata...")
        add_metadata_to_audiobook(
            audio_path=final_path,
            metadata=session['metadata'],
            cover=session.get('cover')
        )

        print(f"✅ Distributed conversion completed: {final_path}")
        return (final_path, True)

    except DistributedModeError as e:
        error_msg = f"Distributed conversion failed: {e}"
        print(error_msg)
        return (error_msg, False)

    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return (error_msg, False)
```

### Modification de convert_ebook

```python
def convert_ebook(args, ctx):
    """Convertit un ebook (mode normal ou distribué)."""

    # Détecter si mode distribué demandé
    if args.get('distributed', False):
        # Vérifier disponibilité
        from lib.distributed_manager import is_distributed_mode_available

        if not is_distributed_mode_available():
            return (
                "Distributed mode not available. "
                "Install: pip install -r requirements-distributed.txt",
                False
            )

        # Utiliser fonction distribuée
        return convert_ebook_distributed(args, ctx)

    # Sinon, mode normal (code existant)
    # ... code existant ...
```

---

## 🧪 Tests Recommandés

### Test 1: Dépendances Manquantes

**Objectif**: Vérifier que l'app fonctionne sans redis/celery installés

```bash
# Désinstaller redis/celery temporairement
pip uninstall -y redis celery

# Lancer l'app (mode normal)
python app.py --headless --ebook test.epub --language eng

# Résultat attendu: ✅ Fonctionne (pas d'erreur)
```

### Test 2: Mode Distribué avec Dépendances

**Objectif**: Vérifier que le mode distribué fonctionne

```bash
# Installer dépendances
pip install -r requirements-distributed.txt

# Démarrer Redis
docker run -d -p 6379:6379 --name test-redis redis:7-alpine

# Démarrer worker
WORKER_ID=test_worker CUDA_VISIBLE_DEVICES=0 python app.py --worker_mode &

# Lancer conversion distribuée
python app.py --headless --distributed --num_workers 1 \
  --ebook test.epub --language eng

# Résultat attendu: ✅ Conversion distribuée fonctionne
```

### Test 3: Mode Distribué sans Redis

**Objectif**: Vérifier gestion d'erreur si Redis down

```bash
# Arrêter Redis
docker stop test-redis

# Tenter conversion distribuée
python app.py --headless --distributed --ebook test.epub

# Résultat attendu: ❌ Message d'erreur clair sur connexion Redis
```

---

## 📊 Checklist de Migration

### Étape 1: Préparation

- [ ] Créer branche `feature/refactor-distributed-mode`
- [ ] Backup du code actuel
- [ ] Vérifier tests existants passent

### Étape 2: Modifications app.py

- [ ] Ajouter imports conditionnels (section 1)
- [ ] Rendre arguments CLI conditionnels (section 2)
- [ ] Refactorer mode worker (section 3)
- [ ] Ajouter support coordinator headless (section 4)

### Étape 3: Modifications functions.py

- [ ] Créer fonction `convert_ebook_distributed()`
- [ ] Modifier fonction `convert_ebook()` pour router
- [ ] Créer fonction `extract_chapters_from_ebook()`
- [ ] Créer fonction `build_tts_config()`

### Étape 4: Tests

- [ ] Test mode normal (sans dépendances distribuées)
- [ ] Test mode distribué (avec Redis)
- [ ] Test gestion d'erreur (Redis down)
- [ ] Test worker mode

### Étape 5: Documentation

- [ ] Mettre à jour README.md
- [ ] Mettre à jour DISTRIBUTED_MODE.md
- [ ] Créer exemples d'utilisation
- [ ] Documenter migration pour utilisateurs existants

### Étape 6: Cleanup

- [ ] Supprimer/renommer `storage.py`
- [ ] Supprimer imports inutiles
- [ ] Vérifier pas de régression
- [ ] Merge dans main

---

## 🔄 Diff Complet app.py

Voici le diff complet des modifications à apporter à `app.py`:

```diff
--- a/app.py
+++ b/app.py
@@ -268,6 +268,18 @@ def main():
                 sys.exit(1)

+        # Import du module distribué (optionnel)
+        try:
+            from lib.distributed_manager import (
+                is_distributed_mode_available,
+                initialize_coordinator,
+                initialize_worker,
+                DistributedModeError
+            )
+            DISTRIBUTED_MODE_AVAILABLE = True
+        except ImportError:
+            DISTRIBUTED_MODE_AVAILABLE = False
+
         from lib.functions import SessionContext, convert_ebook_batch, convert_ebook, web_interface
         ctx = SessionContext()

@@ -225,11 +237,28 @@ def main():
     headless_optional_group.add_argument(options[25], action='version', version=f'ebook2audiobook version {prog_version}', help='''Show the version of the script and exit''')
     headless_optional_group.add_argument(options[26], action='store_true', help=argparse.SUPPRESS)

-    # Distributed mode options
-    distributed_group = parser.add_argument_group('**** Distributed Mode Options (for multi-machine parallelism)', 'Optional')
-    distributed_group.add_argument(options[27], action='store_true', help='''(Optional) Enable distributed processing mode using Celery + Redis. Audio files are transferred directly via Redis (no shared storage needed).''')
-    distributed_group.add_argument(options[28], type=int, default=1, help='''(Optional) Number of workers for distributed processing. Default: 1.''')
-    distributed_group.add_argument(options[29], type=str, default='redis://localhost:6379/0', help='''(Optional) Redis URL for distributed coordination. Default: redis://localhost:6379/0.''')
-    distributed_group.add_argument(options[30], action='store_true', help='''(Optional) Start as a Celery worker (not coordinator).''')
+    # Distributed mode options (conditionnels)
+    if 'DISTRIBUTED_MODE_AVAILABLE' in globals() and DISTRIBUTED_MODE_AVAILABLE:
+        distributed_group = parser.add_argument_group('**** Distributed Mode Options (for multi-machine parallelism)', 'Optional')
+        distributed_group.add_argument('--distributed', action='store_true', help='''(Optional) Enable distributed processing mode using Celery + Redis.''')
+        distributed_group.add_argument('--num_workers', type=int, default=1, help='''(Optional) Number of workers for distributed processing. Default: 1.''')
+        distributed_group.add_argument('--redis_url', type=str, default='redis://localhost:6379/0', help='''(Optional) Redis URL for distributed coordination.''')
+        distributed_group.add_argument('--worker_mode', action='store_true', help='''(Optional) Start as a Celery worker (not coordinator).''')

@@ -273,9 +302,27 @@ def main():

         # Check if starting as worker
         if args.get('worker_mode', False):
+            if not DISTRIBUTED_MODE_AVAILABLE:
+                error = "Cannot start worker: distributed mode dependencies not installed.\nInstall: pip install -r requirements-distributed.txt"
+                print(error)
+                sys.exit(1)
+
             print("Starting Celery worker...")
-            from lib.distributed.worker import start_worker
-            worker_id = os.getenv('WORKER_ID', 'worker_1')
-            gpu_id = os.getenv('CUDA_VISIBLE_DEVICES')
-            start_worker(worker_id=worker_id, gpu_id=gpu_id)
+            try:
+                worker_id = os.getenv('WORKER_ID', 'worker_1')
+                gpu_id = os.getenv('CUDA_VISIBLE_DEVICES')
+                redis_url = args.get('redis_url') or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
+
+                initialize_worker(
+                    worker_id=worker_id,
+                    gpu_id=gpu_id,
+                    redis_url=redis_url
+                )
+            except DistributedModeError as e:
+                error = f"Failed to start worker: {e}"
+                print(error)
+                sys.exit(1)
+            except KeyboardInterrupt:
+                print("\nWorker stopped by user")
+                sys.exit(0)
             return  # Exit after worker stops
```

---

## 🎉 Résultat Final

Après ces modifications:

✅ **Code découplé**: Mode distribué complètement séparé
✅ **Optionnel**: Fonctionne sans redis/celery
✅ **Robuste**: Gestion d'erreur complète
✅ **Maintenable**: Un seul point d'entrée (`distributed_manager.py`)
✅ **Testable**: Facile à mocker et tester

**Temps estimé**: 2-3 heures pour migration complète

---

**Créé le**: 2025-11-07
**Pour la branch**: `claude/distributed-parallelism-mode-011CUsL6fxY6ugbvLQN1LXBw`
