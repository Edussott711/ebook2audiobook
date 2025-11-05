# 🏛️ Architecture du Projet - ebook2audiobook

## 📋 Vue d'ensemble

Ce document décrit l'architecture modulaire du projet `ebook2audiobook` après la refactorisation SRP (Single Responsibility Principle).

---

## 🎯 Objectifs architecturaux

1. **Séparation des préoccupations** - Chaque module a une responsabilité unique
2. **Testabilité** - Modules indépendants et facilement testables
3. **Maintenabilité** - Code organisé et facile à modifier
4. **Évolutivité** - Ajout de nouvelles fonctionnalités simplifié
5. **Réutilisabilité** - Modules indépendants réutilisables

---

## 📁 Structure des répertoires

```
ebook2audiobook/
│
├── app.py                          # Point d'entrée principal
│
├── lib/                            # Bibliothèque principale
│   │
│   ├── core/                       # 🎯 Logique métier centrale
│   │   ├── __init__.py
│   │   ├── exceptions.py           # ✅ Exceptions personnalisées
│   │   │
│   │   ├── session/                # ✅ Gestion de session
│   │   │   ├── __init__.py
│   │   │   ├── session_manager.py  # SessionContext
│   │   │   ├── session_tracker.py  # SessionTracker
│   │   │   └── session_utils.py    # Utilitaires (recursive_proxy)
│   │   │
│   │   └── conversion/             # 🔜 Orchestration de conversion
│   │       ├── __init__.py
│   │       ├── pipeline.py         # Pipeline de conversion
│   │       ├── converter.py        # Conversion ebook unique
│   │       └── batch_converter.py  # Conversion batch
│   │
│   ├── system/                     # 🖥️ Utilitaires système
│   │   ├── __init__.py
│   │   ├── resources.py            # ✅ RAM/VRAM detection
│   │   ├── programs.py             # ✅ Vérification programmes
│   │   └── utils.py                # ✅ Sanitisation, etc.
│   │
│   ├── file/                       # 📁 Gestion de fichiers
│   │   ├── __init__.py
│   │   ├── manager.py              # ✅ Préparation dirs, cleanup
│   │   ├── validator.py            # ✅ Validation fichiers/ZIP
│   │   ├── extractor.py            # ✅ Extraction archives
│   │   ├── hasher.py               # ✅ Calcul/comparaison hash
│   │   └── utils.py                # ✅ proxy2dict, metadata
│   │
│   ├── ebook/                      # 📚 Manipulation d'ebooks
│   │   ├── __init__.py
│   │   ├── extractor.py            # 🔜 Extraction chapitres/métadonnées
│   │   ├── converter.py            # 🔜 Conversion PDF→EPUB
│   │   ├── metadata.py             # 🔜 Gestion métadonnées
│   │   └── models.py               # 🔜 Modèles de données
│   │
│   ├── text/                       # 📝 Traitement de texte
│   │   ├── __init__.py
│   │   ├── processor.py            # 🔜 TextProcessor principal
│   │   ├── normalizer.py           # 🔜 Normalisation de texte
│   │   ├── sentence_splitter.py    # 🔜 Découpage en phrases
│   │   ├── number_converter.py     # 🔜 Nombres → mots
│   │   ├── date_converter.py       # 🔜 Dates/heures → mots
│   │   ├── math_converter.py       # 🔜 Symboles math → mots
│   │   ├── tokenizers/             # 🔜 Tokenizers par langue
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── chinese.py
│   │   │   ├── japanese.py
│   │   │   ├── korean.py
│   │   │   └── thai.py
│   │   └── utils.py
│   │
│   ├── audio/                      # 🔊 Traitement audio
│   │   ├── __init__.py
│   │   ├── converter.py            # 🔜 Chapitres → audio TTS
│   │   ├── combiner.py             # 🔜 Combinaison phrases audio
│   │   ├── exporter.py             # 🔜 Export multi-format
│   │   ├── metadata_generator.py   # 🔜 Métadonnées FFmpeg
│   │   ├── ffmpeg_wrapper.py       # 🔜 Abstraction FFmpeg
│   │   └── utils.py
│   │
│   ├── ui/                         # 🖼️ Interface utilisateur
│   │   ├── __init__.py
│   │   ├── web_interface.py        # 🔜 Point d'entrée Gradio
│   │   ├── components.py           # 🔜 Composants UI
│   │   ├── handlers/               # 🔜 Gestionnaires d'événements
│   │   │   ├── __init__.py
│   │   │   ├── conversion_handler.py
│   │   │   ├── file_handler.py
│   │   │   ├── settings_handler.py
│   │   │   └── player_handler.py
│   │   ├── view_model.py           # 🔜 ViewModel / logique UI
│   │   └── utils.py
│   │
│   ├── classes/                    # Classes existantes (TTS, etc.)
│   │   ├── tts_manager.py
│   │   ├── voice_extractor.py
│   │   ├── background_detector.py
│   │   ├── argos_translator.py
│   │   ├── redirect_console.py
│   │   └── tts_engines/
│   │
│   ├── checkpoint_manager.py       # Gestion checkpoints (OK)
│   ├── conf.py                     # Configuration (OK)
│   ├── lang.py                     # Langues (OK)
│   ├── models.py                   # Modèles TTS (OK)
│   └── functions.py                # 🔜 À déprécier (monolithe)
│
├── tests/                          # 🧪 Tests unitaires
│   ├── __init__.py
│   ├── test_core/
│   │   ├── test_exceptions.py
│   │   └── test_session/
│   ├── test_system/
│   ├── test_file/
│   ├── test_ebook/
│   ├── test_text/
│   ├── test_audio/
│   └── test_ui/
│
├── tools/                          # Outils divers
├── ebooks/                         # Ebooks d'exemple
├── audiobooks/                     # Audiobooks générés
├── voices/                         # Voix TTS
├── models/                         # Modèles TTS
│
├── REFACTORING.md                  # 📘 Documentation refactoring
├── MIGRATION_GUIDE.md              # 📗 Guide de migration
├── ARCHITECTURE.md                 # 📙 Ce document
└── README.md                       # Documentation principale
```

**Légende :**
- ✅ = Implémenté
- 🔜 = À implémenter (Phase 2)

---

## 🔄 Flux de données

### Conversion d'un ebook (mode CLI)

```
┌─────────────┐
│   app.py    │  Point d'entrée
│  (main())   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  lib/core/conversion/converter.py       │  Orchestrateur
│  convert_ebook()                        │
└──────┬──────────────────────────────────┘
       │
       ├─────────────────┐
       │                 │
       ▼                 ▼
┌─────────────┐    ┌──────────────┐
│SessionContext│    │ file/manager│  Préparation
│get_session() │    │prepare_dirs()│
└─────────────┘    └──────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  lib/ebook/converter.py                 │  Conversion EPUB
│  convert2epub()                         │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  lib/ebook/extractor.py                 │  Extraction
│  get_chapters(), get_cover()            │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  lib/text/processor.py                  │  Traitement texte
│  filter_chapter(), normalize_text()     │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  lib/audio/converter.py                 │  Conversion TTS
│  convert_chapters2audio()               │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  lib/audio/exporter.py                  │  Export final
│  combine_audio_chapters()               │
└─────────────────────────────────────────┘
       │
       ▼
    ✅ Audiobook généré
```

### Conversion via interface web (Gradio)

```
┌─────────────┐
│   Browser   │
│  (User)     │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────────────────────────────────┐
│  lib/ui/web_interface.py                │  Interface Gradio
│  web_interface()                        │
└──────┬──────────────────────────────────┘
       │
       ├──────────────────┬─────────────────┐
       │                  │                 │
       ▼                  ▼                 ▼
┌────────────┐   ┌──────────────┐   ┌──────────────┐
│ components │   │  handlers/   │   │ view_model   │
│ (UI layout)│   │ (events)     │   │ (logic)      │
└────────────┘   └──────┬───────┘   └──────────────┘
                        │
                        ▼
                ┌──────────────────┐
                │SessionContext    │  État partagé
                │SessionTracker    │
                └──────┬───────────┘
                       │
                       ▼
                (même flux que CLI ci-dessus)
```

---

## 🧩 Responsabilités des modules

### 1. **lib/core/** - Logique métier centrale

#### core/exceptions.py
**Responsabilité :** Définir et gérer les exceptions de l'application

**Exports :**
```python
- DependencyError       # Dépendances système manquantes
- ConversionError       # Échec de conversion
- ValidationError       # Validation d'entrée échouée
- AudioProcessingError  # Erreur traitement audio
- SessionError          # Erreur gestion session
```

#### core/session/
**Responsabilité :** Gestion centralisée des sessions de conversion

**Modules :**
- `session_manager.py` : Création, stockage, récupération de sessions
- `session_tracker.py` : Suivi du cycle de vie des sessions
- `session_utils.py` : Utilitaires (recursive_proxy)

**Cas d'usage :**
```python
from lib.core.session import SessionContext, SessionTracker

# Créer contexte global
ctx = SessionContext()

# Tracker pour gestion lifecycle
tracker = SessionTracker(ctx)

# Créer/obtenir session
session = ctx.get_session('session-123')
tracker.start_session('session-123')

# Utiliser la session
session['ebook'] = '/path/to/book.epub'
session['progress'] = 50

# Terminer
tracker.end_session('session-123')
```

---

### 2. **lib/system/** - Utilitaires système

#### system/resources.py
**Responsabilité :** Détection ressources matérielles (RAM, VRAM)

**Exports :**
```python
get_ram()   → int  # RAM en GB
get_vram()  → int  # VRAM en GB (0 si non détecté)
```

**Cas d'usage :**
```python
from lib.system import get_ram, get_vram

ram = get_ram()
vram = get_vram()

if ram < 8:
    raise DependencyError("Minimum 8GB RAM required")

if vram >= 4:
    device = 'cuda'  # GPU disponible
else:
    device = 'cpu'   # Fallback CPU
```

#### system/programs.py
**Responsabilité :** Vérification programmes système requis

**Exports :**
```python
check_programs(prog_name, command, options) → (bool, None)
```

**Cas d'usage :**
```python
from lib.system import check_programs

success, _ = check_programs('calibre', 'ebook-convert', '--version')
if not success:
    # DependencyError déjà levée automatiquement
    sys.exit(1)
```

#### system/utils.py
**Responsabilité :** Utilitaires généraux (sanitisation, etc.)

**Exports :**
```python
get_sanitized(text, replacement="_") → str
```

**Cas d'usage :**
```python
from lib.system import get_sanitized

book_title = "Harry Potter: Philosopher's Stone (2001)"
filename = get_sanitized(book_title)
# → "Harry_Potter_Philosopher_s_Stone_2001"
```

---

### 3. **lib/file/** - Gestion de fichiers

#### file/manager.py
**Responsabilité :** Gestion des répertoires et fichiers de conversion

**Exports :**
```python
prepare_dirs(src, session)            → bool
delete_unused_tmp_dirs(dir, days, session) → None
```

**Cas d'usage :**
```python
from lib.file import prepare_dirs, delete_unused_tmp_dirs

# Préparer structure de répertoires
success = prepare_dirs('/path/to/book.epub', session)

# Nettoyer anciens fichiers temporaires
delete_unused_tmp_dirs('/tmp/ebook2audiobook', days=7, session)
```

#### file/validator.py
**Responsabilité :** Validation de fichiers et archives ZIP

**Exports :**
```python
analyze_uploaded_file(zip_path, required_files) → bool
```

**Cas d'usage :**
```python
from lib.file import analyze_uploaded_file

required = ['config.json', 'model.pth', 'vocab.json']
is_valid = analyze_uploaded_file('custom_model.zip', required)

if not is_valid:
    raise ValidationError("Missing required model files")
```

#### file/extractor.py
**Responsabilité :** Extraction de fichiers depuis archives

**Exports :**
```python
extract_custom_model(zip_src, session, required_files, is_gui) → str|None
```

**Cas d'usage :**
```python
from lib.file import extract_custom_model

model_dir = extract_custom_model(
    'my_xtts_model.zip',
    session,
    required_files=['config.json', 'model.pth'],
    is_gui_process=False
)
```

#### file/hasher.py
**Responsabilité :** Calcul et comparaison de hash de fichiers

**Exports :**
```python
calculate_hash(filepath, algorithm='sha256')       → str
compare_files_by_hash(file1, file2, algorithm)    → bool
hash_proxy_dict(proxy_dict)                       → str
compare_dict_keys(d1, d2)                         → dict|None
```

**Cas d'usage :**
```python
from lib.file import calculate_hash, compare_files_by_hash

# Calculer hash
hash1 = calculate_hash('book1.epub')

# Comparer fichiers
if compare_files_by_hash('book1.epub', 'book2.epub'):
    print("Files are identical")
```

#### file/utils.py
**Responsabilité :** Utilitaires divers pour fichiers

**Exports :**
```python
proxy2dict(proxy_obj)                → dict|list|primitive
compare_file_metadata(file1, file2)  → bool
```

---

## 🔌 Dépendances entre modules

### Diagramme de dépendances

```
┌───────────────────────────────────────────────────────────────┐
│                         app.py                                 │
└───────────────────────────────┬───────────────────────────────┘
                                │
                  ┌─────────────┼─────────────┐
                  │             │             │
                  ▼             ▼             ▼
         ┌──────────────┐ ┌─────────┐ ┌──────────────┐
         │   lib/ui/    │ │lib/core/│ │  lib/file/   │
         │              │ │conversion│ │              │
         └──────┬───────┘ └────┬────┘ └──────┬───────┘
                │              │              │
                ▼              ▼              ▼
         ┌──────────────────────────────────────────┐
         │        lib/core/session/                 │
         │     (SessionContext, Tracker)            │
         └──────────────────┬───────────────────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
              ▼             ▼             ▼
      ┌──────────┐  ┌──────────┐  ┌──────────┐
      │lib/ebook/│  │lib/text/ │  │lib/audio/│
      │          │  │          │  │          │
      └────┬─────┘  └────┬─────┘  └────┬─────┘
           │            │             │
           └────────────┼─────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │   lib/system/    │
              │   lib/file/      │
              └──────────────────┘
```

**Règles de dépendance :**
1. ✅ Modules de bas niveau (system, file) → **pas de dépendances** vers modules métier
2. ✅ Modules métier (ebook, text, audio) → peuvent utiliser system/file
3. ✅ core/session → peut utiliser system/file (pas de circular deps)
4. ✅ ui/ → peut utiliser tous les modules (couche présentation)
5. ❌ **Interdiction** de dépendances circulaires

---

## 🧪 Stratégie de tests

### Tests unitaires

```
tests/
├── test_core/
│   ├── test_exceptions.py           # Tester DependencyError, etc.
│   └── test_session/
│       ├── test_session_manager.py  # SessionContext
│       ├── test_session_tracker.py  # SessionTracker
│       └── test_session_utils.py    # recursive_proxy
│
├── test_system/
│   ├── test_resources.py            # get_ram, get_vram (mock psutil)
│   ├── test_programs.py             # check_programs (mock subprocess)
│   └── test_utils.py                # get_sanitized
│
└── test_file/
    ├── test_manager.py              # prepare_dirs, cleanup
    ├── test_validator.py            # analyze_uploaded_file
    ├── test_extractor.py            # extract_custom_model
    └── test_hasher.py               # calculate_hash, compare
```

### Exemple de test

```python
# tests/test_system/test_utils.py
import pytest
from lib.system import get_sanitized

def test_get_sanitized_removes_forbidden_chars():
    input_str = 'Book: Title (2024) <Part 1>'
    result = get_sanitized(input_str)
    assert result == 'Book_Title_2024_Part_1'

def test_get_sanitized_custom_replacement():
    input_str = 'My  Book   Title'
    result = get_sanitized(input_str, replacement="-")
    assert result == 'My-Book-Title'
```

---

## 📈 Évolutivité

### Ajouter un nouveau module

#### Étape 1 : Créer la structure
```bash
mkdir -p lib/nouveau_module
touch lib/nouveau_module/__init__.py
touch lib/nouveau_module/service.py
```

#### Étape 2 : Implémenter le service
```python
# lib/nouveau_module/service.py
"""
Nouveau Module Service
Description de la responsabilité unique.
"""

def ma_fonction(param: str) -> str:
    """
    Description de la fonction.

    Args:
        param: Description du paramètre

    Returns:
        str: Description du retour
    """
    return f"Processed: {param}"
```

#### Étape 3 : Exporter dans __init__.py
```python
# lib/nouveau_module/__init__.py
from .service import ma_fonction

__all__ = ['ma_fonction']
```

#### Étape 4 : Créer les tests
```python
# tests/test_nouveau_module/test_service.py
from lib.nouveau_module import ma_fonction

def test_ma_fonction():
    result = ma_fonction("test")
    assert result == "Processed: test"
```

---

## 🔐 Principes SOLID appliqués

### ✅ Single Responsibility Principle (SRP)
Chaque module a **une seule responsabilité**.
- `system/resources.py` : **uniquement** détection matériel
- `file/hasher.py` : **uniquement** calcul/comparaison hash

### ✅ Open/Closed Principle (OCP)
Modules **ouverts à l'extension, fermés à la modification**.
- Exemple : Ajouter un nouveau tokenizer sans modifier `text/processor.py`

### ✅ Liskov Substitution Principle (LSP)
Les sous-classes peuvent **remplacer** les classes parentes.
- Exemple : Tous les tokenizers implémentent `BaseTokenizer`

### ✅ Interface Segregation Principle (ISP)
Interfaces **spécifiques** plutôt que génériques.
- Exemple : `FileValidator` vs `FileManager` (responsabilités séparées)

### ✅ Dependency Inversion Principle (DIP)
Dépendre des **abstractions**, pas des implémentations.
- Exemple : `TTSManager` accepte n'importe quel TTS engine via interface

---

## 📚 Ressources et références

- **SOLID Principles** : https://en.wikipedia.org/wiki/SOLID
- **Clean Architecture** : https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html
- **Python Best Practices** : https://docs.python-guide.org/
- **Type Hints** : https://docs.python.org/3/library/typing.html

---

## 🎉 Conclusion

L'architecture modulaire de `ebook2audiobook` respecte les principes SOLID et permet :

✅ **Maintenabilité** - Code organisé et facile à modifier
✅ **Testabilité** - Modules indépendants testables unitairement
✅ **Évolutivité** - Ajout de fonctionnalités sans régression
✅ **Lisibilité** - Navigation intuitive par domaine métier
✅ **Réutilisabilité** - Modules indépendants réutilisables

---

**Auteur :** Claude (Anthropic) - Architecte logiciel senior
**Date :** 5 Novembre 2025
**Version :** 1.0
