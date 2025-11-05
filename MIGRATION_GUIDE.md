# 🔄 Guide de Migration - Architecture SRP

## 📋 Vue d'ensemble

Ce guide explique comment **migrer votre code** de l'ancienne architecture monolithique vers la nouvelle architecture modulaire respectant le **Single Responsibility Principle (SRP)**.

---

## 🎯 Principes de migration

### ✅ Compatibilité ascendante

Les nouveaux modules sont conçus pour être **rétro-compatibles**. L'ancien code continue de fonctionner pendant la période de transition.

### 📝 Stratégie de migration

1. **Phase 1** : Les nouveaux modules coexistent avec `lib/functions.py`
2. **Phase 2** : Migration progressive des imports
3. **Phase 3** : Suppression du code monolithique
4. **Phase 4** : Nettoyage et optimisation

---

## 🔀 Table de correspondance des imports

### 1. Gestion de session

#### ❌ Ancien code
```python
from lib.functions import SessionContext, SessionTracker, recursive_proxy
```

#### ✅ Nouveau code
```python
from lib.core.session import SessionContext, SessionTracker, recursive_proxy
```

#### 📝 Changements dans l'API

**SessionContext** - Nouvelles méthodes ajoutées :
```python
ctx = SessionContext()

# Anciennes méthodes (toujours disponibles)
session = ctx.get_session('session-id')
session_id = ctx.find_id_by_hash('socket-hash')

# 🆕 Nouvelles méthodes
exists = ctx.session_exists('session-id')          # Vérifier existence
deleted = ctx.delete_session('session-id')         # Supprimer session
all_ids = ctx.get_all_session_ids()                # Lister toutes les sessions
```

**SessionTracker** - API étendue :
```python
tracker = SessionTracker(context)  # 🆕 context en paramètre

# Anciennes méthodes (toujours disponibles)
tracker.start_session('session-id')
tracker.end_session('session-id', 'socket-hash')

# 🆕 Nouvelles méthodes
is_active = tracker.is_session_active('session-id')
tracker.add_active_socket('socket-hash')
tracker.remove_active_socket('socket-hash')
```

---

### 2. Utilitaires système

#### ❌ Ancien code
```python
from lib.functions import get_ram, get_vram, get_sanitized
```

#### ✅ Nouveau code
```python
from lib.system import get_ram, get_vram, get_sanitized
```

#### 📝 Changements dans l'API

**Aucun changement** - Les signatures de fonctions sont identiques :
```python
# get_ram() → int (RAM en GB)
ram_gb = get_ram()

# get_vram() → int (VRAM en GB, 0 si non détecté)
vram_gb = get_vram()

# get_sanitized(str, replacement="_") → str
filename = get_sanitized("Book: Title (2024)")
```

---

### 3. Vérification des programmes

#### ❌ Ancien code
```python
from lib.functions import check_programs
```

#### ✅ Nouveau code
```python
from lib.system import check_programs
```

#### 📝 Changements dans l'API

**Aucun changement** - Signature identique :
```python
success, _ = check_programs('calibre', 'ebook-convert', '--version')
# Retourne: (True, None) si succès, (False, None) si échec
```

---

### 4. Gestion de fichiers

#### ❌ Ancien code
```python
from lib.functions import (
    prepare_dirs,
    analyze_uploaded_file,
    extract_custom_model,
    calculate_hash,
    compare_files_by_hash,
    proxy2dict
)
```

#### ✅ Nouveau code
```python
from lib.file import (
    prepare_dirs,
    analyze_uploaded_file,
    extract_custom_model,
    calculate_hash,
    compare_files_by_hash,
    proxy2dict
)
```

#### 📝 Changements dans l'API

**prepare_dirs** - Signature identique :
```python
success = prepare_dirs(ebook_path, session)
```

**analyze_uploaded_file** - Signature identique :
```python
is_valid = analyze_uploaded_file('model.zip', required_files=['config.json'])
```

**extract_custom_model** - 🆕 Paramètre optionnel ajouté :
```python
# ❌ Ancien code (is_gui_process était global)
model_dir = extract_custom_model('model.zip', session)

# ✅ Nouveau code (is_gui_process en paramètre explicite)
model_dir = extract_custom_model(
    'model.zip',
    session,
    required_files=None,
    is_gui_process=False  # 🆕 Explicit parameter
)
```

**calculate_hash** - Signature identique :
```python
hash_value = calculate_hash('file.epub', hash_algorithm='sha256')
```

**compare_files_by_hash** - Signature identique :
```python
are_same = compare_files_by_hash('file1.epub', 'file2.epub')
```

**proxy2dict** - Signature identique :
```python
regular_dict = proxy2dict(session_proxy)
```

---

### 5. Exceptions

#### ❌ Ancien code
```python
from lib.functions import DependencyError
```

#### ✅ Nouveau code
```python
from lib.core.exceptions import DependencyError

# 🆕 Nouvelles exceptions disponibles
from lib.core.exceptions import (
    ConversionError,
    ValidationError,
    AudioProcessingError,
    SessionError
)
```

#### 📝 Utilisation

**DependencyError** - Comportement identique :
```python
if not calibre_installed:
    raise DependencyError("Calibre is required")
# Auto-print traceback et exit si not is_gui_process
```

**Nouvelles exceptions** - Usage recommandé :
```python
from lib.core.exceptions import (
    ConversionError,
    ValidationError,
    AudioProcessingError
)

# Validation
if not valid_input:
    raise ValidationError("Invalid ebook format")

# Conversion
if conversion_failed:
    raise ConversionError("Failed to convert EPUB")

# Audio
if audio_export_failed:
    raise AudioProcessingError("Failed to export M4B")
```

---

## 🚀 Exemples de migration complets

### Exemple 1 : Migration d'un module utilisant des sessions

#### ❌ Ancien code
```python
# old_module.py
from lib.functions import SessionContext, get_ram, prepare_dirs

def process_ebook(ebook_path):
    ctx = SessionContext()
    session = ctx.get_session('my-session')

    ram = get_ram()
    print(f"RAM: {ram}GB")

    success = prepare_dirs(ebook_path, session)
    return success
```

#### ✅ Nouveau code
```python
# new_module.py
from lib.core.session import SessionContext
from lib.system import get_ram
from lib.file import prepare_dirs

def process_ebook(ebook_path):
    ctx = SessionContext()
    session = ctx.get_session('my-session')

    ram = get_ram()
    print(f"RAM: {ram}GB")

    success = prepare_dirs(ebook_path, session)
    return success
```

**Changements :**
- ✅ Imports **séparés par domaine** (session, system, file)
- ✅ **Aucun changement** dans la logique métier
- ✅ Code plus **lisible** et **maintenable**

---

### Exemple 2 : Migration avec gestion d'exceptions

#### ❌ Ancien code
```python
from lib.functions import DependencyError, extract_custom_model

def load_model(model_path, session):
    try:
        model_dir = extract_custom_model(model_path, session)
        return model_dir
    except Exception as e:
        DependencyError(str(e))
        return None
```

#### ✅ Nouveau code
```python
from lib.core.exceptions import DependencyError, ValidationError
from lib.file import extract_custom_model

def load_model(model_path, session, is_gui=False):
    try:
        # 🆕 Paramètre is_gui_process explicite
        model_dir = extract_custom_model(
            model_path,
            session,
            is_gui_process=is_gui
        )
        if not model_dir:
            raise ValidationError("Model extraction returned None")
        return model_dir
    except ValidationError as e:
        # 🆕 Exception plus spécifique
        print(f"Validation error: {e}")
        return None
    except Exception as e:
        DependencyError(str(e))
        return None
```

**Améliorations :**
- ✅ Exceptions **plus spécifiques** (ValidationError vs générique Exception)
- ✅ Paramètre `is_gui_process` **explicite**
- ✅ Meilleure **gestion d'erreurs**

---

### Exemple 3 : Migration avec vérification de ressources

#### ❌ Ancien code
```python
from lib.functions import get_ram, get_vram, DependencyError

def check_system_requirements():
    ram = get_ram()
    vram = get_vram()

    if ram < 8:
        DependencyError("Insufficient RAM: need 8GB, have {ram}GB")
        return False

    if vram < 4:
        print("Warning: GPU VRAM < 4GB, using CPU")

    return True
```

#### ✅ Nouveau code
```python
from lib.system import get_ram, get_vram
from lib.core.exceptions import DependencyError

def check_system_requirements():
    ram = get_ram()
    vram = get_vram()

    if ram < 8:
        raise DependencyError(f"Insufficient RAM: need 8GB, have {ram}GB")

    if vram < 4:
        print("Warning: GPU VRAM < 4GB, using CPU")

    return True
```

**Changements :**
- ✅ Imports **séparés** (system vs exceptions)
- ✅ Utilisation de `raise` au lieu d'appeler `DependencyError()` directement (meilleure pratique)

---

## 📊 Checklist de migration

Utilisez cette checklist pour migrer un fichier :

### Étape 1 : Identifier les imports à migrer
- [ ] Lister tous les imports depuis `lib.functions`
- [ ] Identifier le domaine de chaque fonction (session, system, file, etc.)

### Étape 2 : Mettre à jour les imports
- [ ] Remplacer `from lib.functions import X` par les nouveaux modules
- [ ] Grouper les imports par domaine :
  ```python
  # Core
  from lib.core.session import SessionContext
  from lib.core.exceptions import DependencyError

  # System
  from lib.system import get_ram, get_vram

  # File
  from lib.file import prepare_dirs, calculate_hash
  ```

### Étape 3 : Adapter le code si nécessaire
- [ ] Vérifier si des paramètres ont changé (ex: `is_gui_process`)
- [ ] Utiliser les nouvelles exceptions spécifiques
- [ ] Profiter des nouvelles méthodes (ex: `session_exists()`)

### Étape 4 : Tester
- [ ] Vérifier que le code compile sans erreurs
- [ ] Exécuter les tests unitaires
- [ ] Tester manuellement les fonctionnalités

### Étape 5 : Documentation
- [ ] Mettre à jour les docstrings si nécessaire
- [ ] Ajouter des commentaires pour les changements importants

---

## 🔧 Outils de migration automatique

### Script de remplacement automatique (Bash)

```bash
#!/bin/bash
# migrate_imports.sh

# Migrer les imports de session
find . -name "*.py" -type f -exec sed -i \
  's/from lib\.functions import SessionContext/from lib.core.session import SessionContext/g' {} +

# Migrer les imports système
find . -name "*.py" -type f -exec sed -i \
  's/from lib\.functions import get_ram/from lib.system import get_ram/g' {} +

# Migrer les imports de fichiers
find . -name "*.py" -type f -exec sed -i \
  's/from lib\.functions import prepare_dirs/from lib.file import prepare_dirs/g' {} +

echo "Migration des imports terminée !"
```

**⚠️ Attention :** Vérifiez **manuellement** les changements après exécution !

---

## ❓ FAQ - Questions fréquentes

### Q1 : Dois-je migrer tout mon code immédiatement ?
**R :** Non, la migration peut être **progressive**. Les anciens imports depuis `lib.functions` continuent de fonctionner pendant la transition.

### Q2 : Y a-t-il des breaking changes ?
**R :** Un seul changement mineur :
- `extract_custom_model()` : le paramètre `is_gui_process` doit être passé explicitement

### Q3 : Puis-je mélanger anciens et nouveaux imports ?
**R :** Oui, mais c'est **déconseillé**. Préférez une migration complète par fichier.

### Q4 : Les performances sont-elles impactées ?
**R :** Non, aucun impact sur les performances. La refactorisation est **purement structurelle**.

### Q5 : Quand `lib/functions.py` sera-t-il supprimé ?
**R :** Après la Phase 2 complète (tous les modules métier refactorisés). Date estimée : TBD.

### Q6 : Comment tester ma migration ?
**R :**
```bash
# Exécuter les tests
pytest tests/

# Vérifier les imports
python -m py_compile mon_fichier.py
```

---

## 📞 Support

### Problèmes courants

#### Erreur : `ModuleNotFoundError: No module named 'lib.core'`
**Solution :** Vérifiez que vous avez bien les fichiers `__init__.py` :
```bash
ls lib/core/__init__.py
ls lib/system/__init__.py
ls lib/file/__init__.py
```

#### Erreur : `TypeError: extract_custom_model() missing 1 required positional argument: 'is_gui_process'`
**Solution :** Ajoutez le paramètre `is_gui_process` :
```python
extract_custom_model(path, session, is_gui_process=False)
```

---

## 📚 Ressources supplémentaires

- **Documentation complète** : `REFACTORING.md`
- **Architecture détaillée** : Voir section "Nouvelle structure" dans `REFACTORING.md`
- **Exemples de code** : `tests/` (à venir)

---

## 🎉 Conclusion

La migration vers la nouvelle architecture SRP est **simple** et **progressive**. Les bénéfices en termes de **maintenabilité**, **testabilité** et **lisibilité** sont **significatifs**.

**Besoin d'aide ?** Ouvrez une issue sur GitHub avec le tag `migration-help`.

---

**Date de création :** 5 Novembre 2025
**Version :** 1.0
**Dernière mise à jour :** 5 Novembre 2025
