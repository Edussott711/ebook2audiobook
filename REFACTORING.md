# 🏗️ Refactorisation SRP - ebook2audiobook

## 📋 Vue d'ensemble

Ce document décrit la refactorisation majeure du projet `ebook2audiobook` pour respecter le **Single Responsibility Principle (SRP)** et les principes SOLID.

### ❌ Problème identifié

Le fichier `lib/functions.py` contenait **4162 lignes** de code avec **8 responsabilités distinctes** mélangées :
- Gestion de session
- Opérations fichiers/ZIP
- Traitement de texte linguistique
- Traitement audio
- Manipulation EPUB
- Interface web (Gradio)
- Orchestration de conversion
- Utilitaires système

Cette architecture monolithique violait gravement le SRP, rendant le code :
- ❌ Impossible à tester unitairement
- ❌ Difficile à maintenir
- ❌ Complexe pour les nouveaux développeurs
- ❌ Risqué à refactoriser

---

## ✅ Solution : Architecture Modulaire

La nouvelle architecture sépare les responsabilités en **modules cohérents** avec une **responsabilité unique** par module.

### 📁 Nouvelle structure

```
lib/
├── core/                        # 🆕 Logique métier centrale
│   ├── exceptions.py            # ✅ Exceptions centralisées
│   ├── session/                 # ✅ Gestion de session
│   │   ├── session_manager.py   # SessionContext refactorisé
│   │   ├── session_tracker.py   # SessionTracker
│   │   └── session_utils.py     # recursive_proxy, etc.
│   └── conversion/              # 🔜 Orchestration (à implémenter)
│       ├── pipeline.py
│       ├── converter.py
│       └── batch_converter.py
│
├── system/                      # 🆕 Utilitaires système
│   ├── resources.py             # ✅ get_ram(), get_vram()
│   ├── programs.py              # ✅ check_programs()
│   └── utils.py                 # ✅ get_sanitized()
│
├── file/                        # 🆕 Gestion de fichiers
│   ├── manager.py               # ✅ prepare_dirs(), cleanup
│   ├── validator.py             # ✅ analyze_uploaded_file()
│   ├── extractor.py             # ✅ extract_custom_model()
│   ├── hasher.py                # ✅ calculate_hash(), compare
│   └── utils.py                 # ✅ proxy2dict(), metadata
│
├── ebook/                       # 🔜 Manipulation d'ebooks (à implémenter)
│   ├── extractor.py
│   ├── converter.py
│   └── metadata.py
│
├── text/                        # 🔜 Traitement de texte (à implémenter)
│   ├── processor.py
│   ├── normalizer.py
│   ├── sentence_splitter.py
│   └── tokenizers/
│
├── audio/                       # 🔜 Traitement audio (à implémenter)
│   ├── converter.py
│   ├── combiner.py
│   └── exporter.py
│
└── ui/                          # 🔜 Interface utilisateur (à implémenter)
    ├── web_interface.py
    ├── components.py
    └── handlers/
```

---

## 🎯 Modules refactorisés (Phase 1 - Complété)

### 1. **lib/core/exceptions.py**
Centralise toutes les exceptions personnalisées.

#### ✨ Responsabilité unique
Définir et gérer les exceptions de l'application.

#### 📦 Classes exportées
```python
- DependencyError       # Dépendances manquantes
- ConversionError       # Erreurs de conversion
- ValidationError       # Erreurs de validation
- AudioProcessingError  # Erreurs audio
- SessionError          # Erreurs de session
```

#### 📝 Exemple d'utilisation
```python
from lib.core.exceptions import DependencyError

if not calibre_installed:
    raise DependencyError("Calibre is required for EPUB conversion")
```

---

### 2. **lib/system/** - Utilitaires système

#### 2.1 **system/resources.py**
✨ Responsabilité : Détection des ressources système (RAM, VRAM).

```python
from lib.system import get_ram, get_vram

ram_gb = get_ram()      # Retourne RAM en GB
vram_gb = get_vram()    # Retourne VRAM en GB (multi-GPU)
```

**Fonctionnalités :**
- Détection RAM via `psutil`
- Détection VRAM multi-plateforme :
  - NVIDIA (pynvml)
  - AMD (wmic/lspci)
  - Intel (sysfs)
  - macOS (OpenGL)

#### 2.2 **system/programs.py**
✨ Responsabilité : Vérification des programmes système.

```python
from lib.system import check_programs

success, _ = check_programs('calibre', 'ebook-convert', '--version')
```

#### 2.3 **system/utils.py**
✨ Responsabilité : Utilitaires généraux (sanitisation de texte).

```python
from lib.system import get_sanitized

filename = get_sanitized("My Book: Title (2024)", replacement="_")
# Résultat: "My_Book_Title_2024"
```

---

### 3. **lib/file/** - Gestion de fichiers

#### 3.1 **file/manager.py**
✨ Responsabilité : Gestion des répertoires et fichiers.

```python
from lib.file import prepare_dirs, delete_unused_tmp_dirs

# Préparer les répertoires pour la conversion
success = prepare_dirs(ebook_path, session)

# Nettoyer les fichiers temporaires > 7 jours
delete_unused_tmp_dirs(tmp_dir, days=7, session)
```

#### 3.2 **file/validator.py**
✨ Responsabilité : Validation de fichiers et archives.

```python
from lib.file import analyze_uploaded_file

required = ['config.json', 'model.pth', 'vocab.json']
is_valid = analyze_uploaded_file('model.zip', required)
```

#### 3.3 **file/extractor.py**
✨ Responsabilité : Extraction de fichiers depuis archives.

```python
from lib.file import extract_custom_model

model_dir = extract_custom_model(
    'custom_model.zip',
    session,
    required_files=['config.json', 'model.pth'],
    is_gui_process=True
)
```

#### 3.4 **file/hasher.py**
✨ Responsabilité : Calcul et comparaison de hash.

```python
from lib.file import calculate_hash, compare_files_by_hash

hash_value = calculate_hash('ebook.epub', algorithm='sha256')
are_same = compare_files_by_hash('file1.epub', 'file2.epub')
```

#### 3.5 **file/utils.py**
✨ Responsabilité : Utilitaires divers pour fichiers.

```python
from lib.file import proxy2dict, compare_file_metadata

# Convertir proxy multiprocessing en dict
regular_dict = proxy2dict(session_proxy)

# Comparer métadonnées de fichiers
same_metadata = compare_file_metadata('file1.txt', 'file2.txt')
```

---

### 4. **lib/core/session/** - Gestion de session

#### 4.1 **session/session_manager.py**
✨ Responsabilité : Gestion centralisée des sessions.

```python
from lib.core.session import SessionContext

ctx = SessionContext()

# Créer/obtenir une session
session = ctx.get_session('unique-session-id')

# Vérifier l'existence
exists = ctx.session_exists('session-id')

# Supprimer une session
deleted = ctx.delete_session('session-id')

# Lister toutes les sessions
all_ids = ctx.get_all_session_ids()
```

**Fonctionnalités :**
- Création automatique de sessions avec valeurs par défaut
- Support multiprocessing (Manager-backed proxies)
- Gestion des événements d'annulation

#### 4.2 **session/session_tracker.py**
✨ Responsabilité : Suivi du cycle de vie des sessions.

```python
from lib.core.session import SessionTracker

tracker = SessionTracker(context)

# Démarrer une session
started = tracker.start_session('session-id')

# Vérifier si active
is_active = tracker.is_session_active('session-id')

# Terminer une session (ne annule PAS la conversion)
tracker.end_session('session-id', socket_hash='hash123')

# Gérer les sockets actifs
tracker.add_active_socket('socket-hash')
tracker.remove_active_socket('socket-hash')
```

**Thread-safe :** Utilise `threading.Lock` pour les opérations critiques.

#### 4.3 **session/session_utils.py**
✨ Responsabilité : Utilitaires pour sessions (proxies multiprocessing).

```python
from lib.core.session import recursive_proxy

# Convertir dict/list en proxy multiprocessing
proxy_dict = recursive_proxy({
    'key': 'value',
    'nested': {'list': [1, 2, 3]}
}, manager=manager)
```

---

## 📊 Comparaison Avant/Après

| Critère | Avant (Monolithe) | Après (SRP) |
|---------|-------------------|-------------|
| **Fichier principal** | `functions.py` (4162 lignes) | Divisé en 15+ modules |
| **Responsabilités par fichier** | 8 responsabilités mélangées | 1 responsabilité par module |
| **Testabilité** | ❌ Impossible (dépendances couplées) | ✅ Tests unitaires faciles |
| **Lisibilité** | ❌ Complexe (recherche nécessaire) | ✅ Structure claire et intuitive |
| **Maintenabilité** | ❌ Difficile (changements risqués) | ✅ Modifications isolées |
| **Onboarding** | ❌ Cauchemar (4162 lignes à lire) | ✅ Navigation par domaine |
| **Réutilisabilité** | ❌ Couplage fort | ✅ Modules indépendants |
| **Documentation** | ⚠️ Minimale | ✅ Docstrings complètes |

---

## 🚀 Bénéfices de la refactorisation

### 1. **Séparation des préoccupations (SRP)**
✅ Chaque module a une **responsabilité unique** et bien définie.

### 2. **Testabilité améliorée**
✅ Les modules peuvent être testés **indépendamment** sans dépendances complexes.

### 3. **Maintenabilité accrue**
✅ Les modifications dans un domaine (ex: fichiers) n'impactent **pas** les autres (ex: audio).

### 4. **Navigation intuitive**
✅ Structure **logique** par domaine métier :
```
Besoin de gérer des sessions ? → lib/core/session/
Besoin de valider un fichier ? → lib/file/validator.py
Besoin de détecter la RAM ? → lib/system/resources.py
```

### 5. **Réduction du couplage**
✅ Les modules sont **indépendants** et communiquent via des **interfaces claires**.

### 6. **Documentation complète**
✅ Chaque fonction/classe possède des **docstrings** détaillées avec types et exemples.

### 7. **Évolutivité**
✅ Ajouter de nouvelles fonctionnalités est **simple** :
- Nouveau TTS engine ? → Créer `text/tokenizers/nouveau_tokenizer.py`
- Nouveau format audio ? → Ajouter dans `audio/exporter.py`

---

## 🔄 Migration des imports

### Avant (code monolithique)
```python
from lib.functions import (
    get_ram, get_vram, prepare_dirs,
    SessionContext, SessionTracker,
    calculate_hash, compare_files_by_hash
)
```

### Après (architecture modulaire)
```python
# Ressources système
from lib.system import get_ram, get_vram, get_sanitized

# Gestion de fichiers
from lib.file import prepare_dirs, calculate_hash, compare_files_by_hash

# Gestion de session
from lib.core.session import SessionContext, SessionTracker

# Exceptions
from lib.core.exceptions import DependencyError
```

**Avantages :**
- ✅ Imports **explicites** par domaine
- ✅ Auto-complétion **améliorée** dans les IDE
- ✅ Dépendances **tracées** facilement

---

## 📋 Statut de la refactorisation

### ✅ Phase 1 - Complétée (Modules de base)
- [x] `lib/core/exceptions.py` - Exceptions centralisées
- [x] `lib/system/` - Utilitaires système (resources, programs, utils)
- [x] `lib/file/` - Gestion de fichiers (manager, validator, extractor, hasher, utils)
- [x] `lib/core/session/` - Gestion de session (manager, tracker, utils)

### 🔜 Phase 2 - À implémenter (Modules métier)
- [ ] `lib/ebook/` - Manipulation EPUB (extractor, converter, metadata)
- [ ] `lib/text/` - Traitement de texte (processor, normalizer, tokenizers)
- [ ] `lib/audio/` - Traitement audio (converter, combiner, exporter)
- [ ] `lib/core/conversion/` - Orchestration conversion (pipeline, converter)
- [ ] `lib/ui/` - Interface web (components, handlers, view_model)

### 🧪 Phase 3 - Tests (À créer)
- [ ] Tests unitaires pour chaque module
- [ ] Tests d'intégration
- [ ] Couverture de code > 80%

---

## 👥 Guide pour les développeurs

### Comment contribuer à la refactorisation ?

1. **Choisir un module à refactoriser** (voir Phase 2)
2. **Créer la structure** :
   ```bash
   mkdir -p lib/nouveau_module
   touch lib/nouveau_module/__init__.py
   ```
3. **Extraire les fonctions** depuis `lib/functions.py`
4. **Ajouter des docstrings** complètes (types, args, returns, examples)
5. **Créer des tests** dans `tests/test_nouveau_module/`
6. **Mettre à jour les imports** dans les fichiers existants

### Règles à respecter

✅ **DO (À faire)**
- Une **responsabilité unique** par module
- Docstrings **complètes** avec type hints
- Tests unitaires pour **chaque fonction publique**
- Noms de fonctions/classes **explicites**
- Gestion d'erreurs **cohérente** (exceptions personnalisées)

❌ **DON'T (À éviter)**
- Mélanger plusieurs responsabilités dans un fichier
- Dépendances circulaires entre modules
- Fonctions de plus de 50 lignes (sauf exceptions justifiées)
- Imports wildcard (`from module import *`)
- Code sans documentation

---

## 📚 Ressources

- **SOLID Principles** : https://en.wikipedia.org/wiki/SOLID
- **Single Responsibility Principle** : https://en.wikipedia.org/wiki/Single-responsibility_principle
- **Python Type Hints** : https://docs.python.org/3/library/typing.html
- **Google Python Style Guide** : https://google.github.io/styleguide/pyguide.html

---

## 🙏 Remerciements

Cette refactorisation a été réalisée pour améliorer la **qualité du code**, la **maintenabilité** et l'**expérience développeur** du projet ebook2audiobook.

**Auteur de la refactorisation :** Claude (Anthropic) - Architecte logiciel senior
**Date :** 5 Novembre 2025
**Version :** 1.0

---

**Questions ou suggestions ?** Ouvrez une issue sur GitHub ou consultez le guide de migration (`MIGRATION_GUIDE.md`).
