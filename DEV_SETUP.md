# 🚀 Configuration Rapide de l'Environnement de Développement

Ce guide vous permet de démarrer rapidement avec l'environnement de développement Docker.

## ⚡ Démarrage Ultra-Rapide (3 étapes)

### Option 1: VSCode Dev Container (Recommandé)

```bash
# 1. Ouvrir le projet dans VSCode
code .

# 2. Appuyer sur F1 et taper:
Dev Containers: Reopen in Container

# 3. C'est tout! ✨
```

### Option 2: Script Automatique

```bash
# 1. Rendre le script exécutable (déjà fait)
chmod +x dev.sh

# 2. Lancer le menu interactif
./dev.sh

# 3. Choisir l'option 1 pour build, puis 2 pour démarrer
```

### Option 3: Docker Compose Manuel

```bash
# 1. Build
docker-compose -f docker-compose.dev.yml build

# 2. Start
docker-compose -f docker-compose.dev.yml up -d

# 3. Shell
docker-compose -f docker-compose.dev.yml exec dev zsh
```

## 📦 Ce qui est inclus

### Outils de Développement
- ✅ Python 3.12
- ✅ pytest (tests)
- ✅ black (formatage)
- ✅ flake8 (linting)
- ✅ mypy (type checking)
- ✅ pylint (analyse)
- ✅ pre-commit hooks
- ✅ ipython/ipdb (débogage)

### Configuration Automatique
- ✅ Extensions VSCode
- ✅ Formatage à la sauvegarde
- ✅ Linting en temps réel
- ✅ Auto-complétion
- ✅ Support GPU (NVIDIA)

### Volumes Persistants
- ✅ Environnement virtuel Python
- ✅ Modèles TTS téléchargés
- ✅ Caches (pip, pytest, mypy)

## 🎯 Commandes Rapides

### Dans le Container (après ./dev.sh option 5)

```bash
# Tests
pytest                    # Tous les tests
pytest -m "not slow"      # Tests rapides
make test                 # Avec couverture

# Formatage
black .                   # Formater le code
isort .                   # Trier les imports
make format               # Les deux

# Linting
flake8 .                  # Style guide
mypy .                    # Type checking
pylint lib                # Analyse complète
make lint                 # Tous les linters

# Application
python app.py             # Interface web
make run                  # Pareil

# Pre-commit
pre-commit run --all-files   # Tous les hooks
```

### Depuis l'Hôte

```bash
# Script interactif
./dev.sh                  # Menu complet

# Docker Compose
docker-compose -f docker-compose.dev.yml up -d      # Démarrer
docker-compose -f docker-compose.dev.yml down       # Arrêter
docker-compose -f docker-compose.dev.yml exec dev zsh  # Shell

# Makefile
make docker-build         # Build
make docker-up            # Start
make docker-shell         # Shell
```

## 📁 Fichiers Créés

```
.
├── .devcontainer/           # Configuration Dev Container
│   ├── devcontainer.json   # Config VSCode
│   ├── Dockerfile          # Image dev
│   ├── entrypoint.sh       # Script démarrage
│   ├── post-create.sh      # Post-création
│   └── README.md           # Doc devcontainer
├── tests/                   # Structure de tests
│   ├── __init__.py
│   ├── conftest.py         # Fixtures pytest
│   └── test_example.py     # Tests exemples
├── .flake8                  # Config flake8
├── .pre-commit-config.yaml  # Pre-commit hooks
├── .editorconfig           # Config éditeur
├── pyproject.toml          # Config Python tools (mis à jour)
├── requirements-dev.txt    # Dépendances dev
├── docker-compose.dev.yml  # Docker Compose dev
├── Makefile                # Commandes make
├── dev.sh                  # Script launcher
├── DEVELOPMENT.md          # Documentation complète
└── DEV_SETUP.md            # Ce fichier
```

## 🔧 Configuration

### Prérequis
- Docker >= 20.10
- Docker Compose >= 2.0
- VSCode (pour Dev Container)
- NVIDIA GPU + drivers (optionnel, pour accélération)

### Ports
- `7860` - Interface web Gradio

### GPU Support
Le container est configuré pour utiliser le GPU NVIDIA si disponible.

Pour vérifier:
```bash
docker-compose -f docker-compose.dev.yml exec dev nvidia-smi
```

## 📚 Documentation

- **DEVELOPMENT.md** - Guide complet de développement
- **.devcontainer/README.md** - Doc Dev Container
- **Makefile** - Liste des commandes disponibles

## 🐛 Problèmes Courants

### Container ne démarre pas
```bash
# Vérifier Docker
docker ps

# Voir les logs
docker-compose -f docker-compose.dev.yml logs

# Rebuild
docker-compose -f docker-compose.dev.yml build --no-cache
```

### Permissions
```bash
# Si fichiers en root
sudo chown -R $USER:$USER .
```

### GPU non détecté
```bash
# Vérifier NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

## 💡 Workflow Recommandé

1. **Ouvrir VSCode Dev Container**
2. **Créer une branche**
   ```bash
   git checkout -b feature/ma-feature
   ```
3. **Développer avec auto-save formatting**
4. **Tester**
   ```bash
   pytest
   ```
5. **Commit** (pre-commit hooks s'exécutent auto)
   ```bash
   git add .
   git commit -m "feat: ma feature"
   ```
6. **Push**
   ```bash
   git push origin feature/ma-feature
   ```

## 🎓 Ressources

- [Guide Développement Complet](DEVELOPMENT.md)
- [VSCode Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers)
- [pytest Documentation](https://docs.pytest.org/)
- [pre-commit](https://pre-commit.com/)

---

**Questions?** Consultez `DEVELOPMENT.md` pour plus de détails!
