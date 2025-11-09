# 🧪 Guide Pytest avec Docker

## 📦 Structure des Tests

```
tests/
├── conftest.py              # Configuration pytest
├── test_audio/              # Tests modules audio
│   ├── test_converter.py
│   ├── test_combiner.py
│   └── test_exporter.py
├── test_text/               # Tests modules text
│   ├── test_date_converter.py
│   ├── test_math_converter.py
│   ├── test_number_converter.py
│   ├── test_processor.py
│   └── test_sentence_splitter.py
├── test_ebook/              # Tests modules ebook
├── test_file/               # Tests modules file
└── test_core/               # Tests modules core
```

---

## 🚀 Lancer TOUS les tests

```bash
# Build l'image
docker build -t ebook2audiobook .

# Lancer tous les tests
docker run --rm --entrypoint pytest ebook2audiobook tests/ -v
```

**Options utiles:**
- `-v` : Mode verbose (affiche détails)
- `-vv` : Mode très verbose
- `-x` : Stop au premier échec
- `-s` : Affiche les prints
- `--tb=short` : Traceback court

---

## 🎯 Lancer des tests SPÉCIFIQUES

### 1️⃣ Tests par module

```bash
# Tests audio uniquement
docker run --rm --entrypoint pytest ebook2audiobook tests/test_audio/ -v

# Tests text uniquement
docker run --rm --entrypoint pytest ebook2audiobook tests/test_text/ -v

# Tests ebook uniquement
docker run --rm --entrypoint pytest ebook2audiobook tests/test_ebook/ -v

# Tests file uniquement
docker run --rm --entrypoint pytest ebook2audiobook tests/test_file/ -v

# Tests core uniquement
docker run --rm --entrypoint pytest ebook2audiobook tests/test_core/ -v
```

### 2️⃣ Tests par fichier

```bash
# Un fichier spécifique
docker run --rm --entrypoint pytest ebook2audiobook tests/test_text/test_date_converter.py -v

# Plusieurs fichiers
docker run --rm --entrypoint pytest ebook2audiobook \
  tests/test_text/test_date_converter.py \
  tests/test_text/test_math_converter.py \
  -v
```

### 3️⃣ Tests par fonction

```bash
# Une fonction spécifique
docker run --rm --entrypoint pytest ebook2audiobook \
  tests/test_text/test_date_converter.py::test_year2words -v

# Pattern matching
docker run --rm --entrypoint pytest ebook2audiobook \
  tests/test_text/ -k "test_year" -v
```

---

## 📊 Rapport de Couverture

```bash
# Avec couverture de code
docker run --rm --entrypoint pytest ebook2audiobook tests/ \
  --cov=lib \
  --cov-report=html \
  --cov-report=term

# Copier le rapport HTML hors du conteneur
docker run --rm -v $(pwd)/htmlcov:/app/htmlcov ebook2audiobook \
  pytest tests/ --cov=lib --cov-report=html

# Puis ouvrir htmlcov/index.html dans un navigateur
```

---

## 🐛 Mode Debug

```bash
# Avec pdb (debugger Python)
docker run --rm -it --entrypoint pytest ebook2audiobook tests/ --pdb

# Afficher les prints
docker run --rm --entrypoint pytest ebook2audiobook tests/ -s

# Traceback complet
docker run --rm --entrypoint pytest ebook2audiobook tests/ --tb=long
```

---

## ⚡ Tests Parallèles

```bash
# Installer pytest-xdist (si pas déjà dans requirements)
# Puis lancer en parallèle

docker run --rm --entrypoint pytest ebook2audiobook tests/ -n auto -v

# Spécifier nombre de workers
docker run --rm --entrypoint pytest ebook2audiobook tests/ -n 4 -v
```

---

## 🔍 Tests avec Filtres

```bash
# Tests qui contiennent "converter" dans le nom
docker run --rm --entrypoint pytest ebook2audiobook tests/ -k "converter" -v

# Tests SAUF ceux qui contiennent "slow"
docker run --rm --entrypoint pytest ebook2audiobook tests/ -k "not slow" -v

# Plusieurs patterns
docker run --rm --entrypoint pytest ebook2audiobook tests/ -k "audio or text" -v
```

---

## 📝 Markers (si configurés dans conftest.py)

```bash
# Tests marqués comme "unit"
docker run --rm --entrypoint pytest ebook2audiobook tests/ -m "unit" -v

# Tests marqués comme "integration"
docker run --rm --entrypoint pytest ebook2audiobook tests/ -m "integration" -v

# Tests marqués comme "slow"
docker run --rm --entrypoint pytest ebook2audiobook tests/ -m "slow" -v

# Exclure un marker
docker run --rm --entrypoint pytest ebook2audiobook tests/ -m "not slow" -v
```

---

## 🔁 Re-run Tests Échoués

```bash
# Premier run
docker run --rm --entrypoint pytest ebook2audiobook tests/ -v

# Re-run seulement les tests échoués
docker run --rm --entrypoint pytest ebook2audiobook tests/ --lf -v

# Re-run échoués d'abord, puis tous
docker run --rm --entrypoint pytest ebook2audiobook tests/ --ff -v
```

---

## 📈 Rapport JUnit (CI/CD)

```bash
# Générer rapport JUnit XML
docker run --rm -v $(pwd)/reports:/app/reports ebook2audiobook \
  pytest tests/ --junitxml=reports/junit.xml

# Le fichier junit.xml sera dans ./reports/
```

---

## 🛠️ Tests avec Variables d'Environnement

```bash
# Passer des variables d'environnement
docker run --rm \
  -e TEST_MODE=integration \
  -e DEBUG=1 \
  ebook2audiobook pytest tests/ -v
```

---

## 🎨 Sortie Colorée

```bash
# Activer les couleurs
docker run --rm -t --entrypoint pytest ebook2audiobook tests/ --color=yes -v

# Désactiver les couleurs
docker run --rm --entrypoint pytest ebook2audiobook tests/ --color=no -v
```

---

## 📦 Tests avec Volumes (pour fichiers de test)

```bash
# Si tests nécessitent des fichiers externes
docker run --rm \
  -v $(pwd)/test_files:/app/test_files \
  ebook2audiobook pytest tests/ -v
```

---

## 🚦 Quick Smoke Test

```bash
# Test rapide : 1 test par module pour vérifier que tout importe
docker run --rm --entrypoint pytest ebook2audiobook tests/ --maxfail=1 -x -v
```

---

## 📋 Exemples Complets

### Test Complet avec Rapport

```bash
docker run --rm \
  -v $(pwd)/reports:/app/reports \
  ebook2audiobook \
  pytest tests/ \
    -v \
    --cov=lib \
    --cov-report=html:reports/coverage \
    --cov-report=term \
    --junitxml=reports/junit.xml \
    --tb=short
```

### Test Rapide de Développement

```bash
# Tests texte seulement, verbose, stop au premier échec
docker run --rm ebook2audiobook \
  pytest tests/test_text/ -vv -x -s
```

### Test de Régression

```bash
# Tous les tests, parallèle, rapport complet
docker run --rm ebook2audiobook \
  pytest tests/ -n auto --tb=short --maxfail=5
```

---

## 🔧 Commandes Utiles

```bash
# Lister tous les tests sans les exécuter
docker run --rm --entrypoint pytest ebook2audiobook tests/ --collect-only

# Afficher les fixtures disponibles
docker run --rm --entrypoint pytest ebook2audiobook tests/ --fixtures

# Statistiques détaillées
docker run --rm --entrypoint pytest ebook2audiobook tests/ -v --durations=10

# Version de pytest
docker run --rm --entrypoint pytest ebook2audiobook --version
```

---

## 📊 Script de Test Complet

Créer `run-tests.sh`:

```bash
#!/bin/bash
set -e

echo "🧪 Running pytest in Docker..."
echo ""

# Build
echo "📦 Building image..."
docker build -t ebook2audiobook . -q

# Tests
echo "🚀 Running tests..."
docker run --rm \
  -v $(pwd)/reports:/app/reports \
  ebook2audiobook \
  pytest tests/ \
    -v \
    --cov=lib \
    --cov-report=term-missing \
    --cov-report=html:reports/coverage \
    --junitxml=reports/junit.xml \
    --tb=short \
    --maxfail=10

echo ""
echo "✅ Tests completed!"
echo "📊 Coverage report: reports/coverage/index.html"
echo "📝 JUnit report: reports/junit.xml"
```

Utilisation:
```bash
chmod +x run-tests.sh
./run-tests.sh
```

---

## ❌ Troubleshooting

### Problème: Module not found

```bash
# Vérifier le PYTHONPATH dans le conteneur
docker run --rm ebook2audiobook python3 -c "import sys; print('\n'.join(sys.path))"

# Forcer le PYTHONPATH
docker run --rm \
  -e PYTHONPATH=/app \
  ebook2audiobook pytest tests/ -v
```

### Problème: Tests ne trouvent pas les fichiers

```bash
# Vérifier le working directory
docker run --rm ebook2audiobook pwd

# Forcer le working directory
docker run --rm -w /app --entrypoint pytest ebook2audiobook tests/ -v
```

### Problème: Import des modules SRP

```bash
# Vérifier les imports
docker run --rm ebook2audiobook python3 -c "
import sys
sys.path.insert(0, '/app')
from lib.audio.converter import convert_chapters2audio
from lib.text.processor import filter_chapter
print('✅ Imports OK')
"
```

---

## 📚 Ressources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [pytest-xdist](https://pytest-xdist.readthedocs.io/)

---

## ✅ Checklist Rapide

```bash
# 1. Tests passent ?
docker run --rm --entrypoint pytest ebook2audiobook tests/ -v

# 2. Couverture OK ?
docker run --rm --entrypoint pytest ebook2audiobook tests/ --cov=lib --cov-report=term

# 3. Pas de tests cassés ?
docker run --rm --entrypoint pytest ebook2audiobook tests/ --tb=short

# 4. Performance OK ?
docker run --rm --entrypoint pytest ebook2audiobook tests/ --durations=10
```

🎯 **Commande recommandée pour développement:**
```bash
docker run --rm --entrypoint pytest ebook2audiobook tests/ -v --tb=short -x
```
