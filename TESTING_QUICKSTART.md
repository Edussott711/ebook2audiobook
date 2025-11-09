# 🚀 Testing Quickstart

## 🎯 Commandes Rapides

### Tests Automatisés Complets
```bash
./test-docker.sh          # Tests de validation rapides (build, imports, proxy2dict)
./run-tests.sh            # Tous les tests pytest
```

### Tests Pytest Spécifiques
```bash
./run-tests.sh audio      # Tests audio uniquement
./run-tests.sh text       # Tests text uniquement
./run-tests.sh quick      # Smoke test rapide
./run-tests.sh coverage   # Avec rapport de couverture
./run-tests.sh parallel   # Tests en parallèle
./run-tests.sh debug      # Mode debug avec pdb
```

### Tests Docker Manuels
```bash
# Tous les tests
docker run --rm ebook2audiobook pytest tests/ -v

# Un module spécifique
docker run --rm ebook2audiobook pytest tests/test_text/ -v

# Un fichier spécifique
docker run --rm ebook2audiobook pytest tests/test_text/test_date_converter.py -v

# Une fonction spécifique
docker run --rm ebook2audiobook pytest tests/test_text/test_date_converter.py::test_year2words -v
```

---

## 📚 Documentation Complète

- **RUN_PYTEST_DOCKER.md** - Guide complet pytest + Docker
- **DOCKER_TEST_CHECKLIST.md** - Checklist tests manuels
- **test-docker.sh** - Script de validation automatique
- **run-tests.sh** - Script pytest interactif

---

## ✅ Workflow Recommandé

### 1️⃣ Développement
```bash
# Test rapide pendant le dev
./run-tests.sh quick

# Tests du module en cours
./run-tests.sh text      # ou audio, ebook, file, core
```

### 2️⃣ Avant Commit
```bash
# Tous les tests
./run-tests.sh

# Avec couverture
./run-tests.sh coverage
```

### 3️⃣ Validation Complète
```bash
# Tests automatisés
./test-docker.sh

# Tests pytest
./run-tests.sh coverage

# Tests manuels Gradio
docker run -p 7860:7860 ebook2audiobook
```

---

## 🐛 Debug

```bash
# Tests échoués ? Re-run en debug
./run-tests.sh debug

# Tests échoués ? Re-run seulement ceux-là
./run-tests.sh failed

# Voir les détails d'un test
docker run --rm ebook2audiobook pytest tests/test_text/test_date_converter.py -vv -s
```

---

## 📊 Rapports

Après `./run-tests.sh coverage`:
- **HTML**: Ouvrir `reports/coverage/index.html`
- **JUnit**: `reports/junit.xml` (pour CI/CD)

---

## 🎓 Exemples

### Test une nouvelle fonctionnalité
```bash
# 1. Écrire le test dans tests/test_xxx/
# 2. Lancer le test
docker run --rm ebook2audiobook pytest tests/test_xxx/test_new_feature.py -v

# 3. Itérer jusqu'à ce que ça passe
./run-tests.sh quick
```

### Vérifier la couverture d'un module
```bash
docker run --rm ebook2audiobook pytest tests/test_text/ \
  --cov=lib.text \
  --cov-report=term-missing
```

### Test de régression
```bash
# Tous les tests, stop si plus de 5 échecs
docker run --rm ebook2audiobook pytest tests/ -v --maxfail=5
```

---

## 💡 Tips

- Utiliser `./run-tests.sh quick` en boucle rapide de dev
- Utiliser `./run-tests.sh coverage` avant commit
- Utiliser `./test-docker.sh` pour validation build/imports
- Les rapports sont dans `reports/`
- Logs détaillés avec `-vv -s`

---

## ⚡ Raccourcis Shell (optionnel)

Ajouter à ton `.bashrc` ou `.zshrc`:

```bash
alias pt='./run-tests.sh'
alias ptq='./run-tests.sh quick'
alias ptc='./run-tests.sh coverage'
alias ptd='./run-tests.sh debug'
```

Puis:
```bash
pt         # Tous les tests
ptq        # Quick test
ptc        # Avec couverture
ptd        # Mode debug
```

---

## 📦 Structure Complète

```
ebook2audiobook/
├── tests/                      # Tests pytest
│   ├── conftest.py
│   ├── test_audio/
│   ├── test_text/
│   ├── test_ebook/
│   ├── test_file/
│   └── test_core/
├── test-docker.sh              # Validation build/imports
├── run-tests.sh                # Runner pytest interactif
├── RUN_PYTEST_DOCKER.md        # Guide complet
├── DOCKER_TEST_CHECKLIST.md    # Checklist manuelle
└── TESTING_QUICKSTART.md       # Ce fichier
```

🎯 **Commande la plus utile:** `./run-tests.sh quick` pour un feedback rapide !
