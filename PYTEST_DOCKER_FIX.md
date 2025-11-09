# 🔧 Fix: pytest avec Docker - ENTRYPOINT Override

## ⚠️ Problèmes

### 1. ENTRYPOINT Docker
Le Dockerfile contient :
```dockerfile
ENTRYPOINT ["python", "app.py", "--script_mode", "full_docker"]
```

Donc quand tu lances :
```bash
docker run ebook2audiobook pytest tests/
```

Docker exécute en réalité :
```bash
python app.py --script_mode full_docker pytest tests/
```

Ce qui essaie de passer `pytest tests/` comme arguments à `app.py` → **ERREUR** !

```
app.py: error: unrecognized arguments: pytest tests/
```

### 2. pytest pas dans PATH
pytest peut être installé mais pas dans le PATH du conteneur :
```
exec: "pytest": executable file not found in $PATH
```

---

## ✅ Solution

**Utiliser `python3 -m pytest`** pour override le ENTRYPOINT et exécuter pytest via Python :

```bash
docker run --rm --entrypoint "python3 -m pytest" ebook2audiobook tests/ -v
```

**OU rebuild l'image** après avoir ajouté pytest à requirements.txt (déjà fait dans le code) :
```bash
docker build -t ebook2audiobook .
docker run --rm --entrypoint pytest ebook2audiobook tests/ -v
```

---

## 📝 Commandes Corrigées

### Tous les tests
```bash
docker run --rm --entrypoint "python3 -m pytest" ebook2audiobook tests/ -v
```

### Tests par module
```bash
docker run --rm --entrypoint "python3 -m pytest" ebook2audiobook tests/test_audio/ -v
docker run --rm --entrypoint "python3 -m pytest" ebook2audiobook tests/test_text/ -v
```

### Avec couverture
```bash
docker run --rm --entrypoint "python3 -m pytest" ebook2audiobook tests/ \
  --cov=lib --cov-report=term -v
```

### Debug mode
```bash
docker run --rm -it --entrypoint "python3 -m pytest" ebook2audiobook tests/ -vv -s --pdb
```

---

## 🚀 Scripts Automatiques (Déjà corrigés)

Les scripts fournis utilisent déjà `python3 -m pytest` :

```bash
./run-tests.sh              # Utilise --entrypoint "python3 -m pytest"
./run-tests.sh quick        # Utilise --entrypoint "python3 -m pytest"
./run-tests.sh coverage     # Utilise --entrypoint "python3 -m pytest"
```

✅ **Utilise simplement les scripts fournis !**

---

## 🔍 Explication Technique

### Sans --entrypoint (❌ Erreur)
```bash
docker run ebook2audiobook pytest tests/
# Exécute: python app.py --script_mode full_docker pytest tests/
# Résultat: app.py essaie de parser "pytest tests/" comme arguments
# Erreur: unrecognized arguments: pytest tests/
```

### Avec --entrypoint pytest (❌ Erreur si pytest pas dans PATH)
```bash
docker run --entrypoint pytest ebook2audiobook tests/
# Override le ENTRYPOINT
# Exécute: pytest tests/
# Erreur: exec: "pytest": executable file not found in $PATH
```

### Avec --entrypoint "python3 -m pytest" (✅ Correct)
```bash
docker run --entrypoint "python3 -m pytest" ebook2audiobook tests/
# Override le ENTRYPOINT
# Exécute: python3 -m pytest tests/
# Résultat: pytest lance correctement les tests via Python
```

---

## 📚 Alternative: Lancer app.py pour Gradio

Si tu veux lancer Gradio (pas pytest), n'utilise PAS `--entrypoint` :

```bash
# Gradio interface
docker run -p 7860:7860 ebook2audiobook

# Headless conversion
docker run ebook2audiobook --headless --ebook /path/to/book.epub

# Ces commandes utilisent le ENTRYPOINT par défaut (app.py)
```

---

## 🎯 Résumé

| But | Commande | Utilise --entrypoint ? |
|-----|----------|------------------------|
| **Pytest** | `docker run --entrypoint "python3 -m pytest" ebook2audiobook tests/` | ✅ OUI |
| **Gradio GUI** | `docker run -p 7860:7860 ebook2audiobook` | ❌ NON |
| **Headless** | `docker run ebook2audiobook --headless --ebook test.epub` | ❌ NON |
| **Scripts** | `./run-tests.sh` | ✅ Déjà intégré |

---

## ✅ Quick Check

Teste que ça marche :
```bash
# Doit afficher la version de pytest
docker run --rm --entrypoint "python3 -m pytest" ebook2audiobook --version

# Doit lister les tests
docker run --rm --entrypoint "python3 -m pytest" ebook2audiobook tests/ --collect-only

# Doit lancer les tests
docker run --rm --entrypoint "python3 -m pytest" ebook2audiobook tests/ -v
```

**Après rebuild** (avec pytest dans requirements.txt) :
```bash
docker build -t ebook2audiobook .
docker run --rm --entrypoint pytest ebook2audiobook --version
docker run --rm --entrypoint pytest ebook2audiobook tests/ -v
```

---

## 💡 Tips

1. **Utiliser `python3 -m pytest`** pour les tests (ou rebuild après ajout de pytest à requirements.txt)
2. **Utiliser les scripts fournis** (`./run-tests.sh`) qui gèrent ça automatiquement
3. **Ne PAS utiliser `--entrypoint`** pour lancer Gradio ou conversions
4. **Rebuild l'image** pour installer pytest proprement : `docker build -t ebook2audiobook .`
