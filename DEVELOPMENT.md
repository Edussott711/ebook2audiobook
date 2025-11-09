# Guide de Développement - eBook2Audiobook

Ce guide vous aidera à configurer et utiliser l'environnement de développement Docker pour le projet eBook2Audiobook.

## Table des Matières

1. [Prérequis](#prérequis)
2. [Configuration Rapide](#configuration-rapide)
3. [Utilisation du Dev Container](#utilisation-du-dev-container)
4. [Outils de Développement](#outils-de-développement)
5. [Tests](#tests)
6. [Linting et Formatage](#linting-et-formatage)
7. [Workflow de Développement](#workflow-de-développement)
8. [Dépannage](#dépannage)

## Prérequis

### Requis
- Docker >= 20.10
- Docker Compose >= 2.0
- Visual Studio Code (recommandé)
- Extension VSCode "Dev Containers" (ms-vscode-remote.remote-containers)

### Optionnel (pour support GPU)
- NVIDIA GPU
- NVIDIA Docker Runtime
- CUDA >= 11.0

## Configuration Rapide

### Option 1: VSCode Dev Container (Recommandé)

1. **Ouvrir le projet dans VSCode**
   ```bash
   code .
   ```

2. **Ouvrir dans le Dev Container**
   - Appuyez sur `F1` ou `Ctrl+Shift+P`
   - Tapez "Dev Containers: Reopen in Container"
   - Appuyez sur Entrée

3. **Attendre la construction**
   - Le container sera construit automatiquement
   - Les dépendances seront installées
   - Le terminal sera prêt dans le container

### Option 2: Docker Compose Manuel

1. **Construire le container**
   ```bash
   docker-compose -f docker-compose.dev.yml build
   ```

2. **Démarrer le container**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

3. **Entrer dans le container**
   ```bash
   docker-compose -f docker-compose.dev.yml exec dev zsh
   ```

## Utilisation du Dev Container

### Structure du Projet

```
ebook2audiobook/
├── .devcontainer/           # Configuration Dev Container
│   ├── devcontainer.json   # Configuration VSCode
│   ├── Dockerfile          # Image de développement
│   ├── entrypoint.sh       # Script de démarrage
│   └── post-create.sh      # Script post-création
├── tests/                   # Tests unitaires et d'intégration
├── lib/                     # Code source principal
├── pyproject.toml          # Configuration Python et outils
├── requirements.txt        # Dépendances de production
├── requirements-dev.txt    # Dépendances de développement
└── docker-compose.dev.yml  # Configuration Docker Compose dev
```

### Accès au Container

**Terminal intégré VSCode:**
- Ouvre automatiquement dans le container
- Utilise Zsh avec Oh My Zsh

**Ports exposés:**
- `7860`: Interface Gradio Web UI

### Volumes Persistants

Les données suivantes sont persistées entre les redémarrages:
- `.venv/` - Environnement virtuel Python
- `models/` - Modèles TTS téléchargés
- Cache pip, pytest, mypy

## Outils de Développement

### Python

**Version:** Python 3.12
**Gestionnaire de paquets:** pip
**Environnement virtuel:** Géré automatiquement

### Outils Installés

| Outil | Description | Commande |
|-------|-------------|----------|
| **pytest** | Framework de tests | `pytest` |
| **black** | Formatage de code | `black .` |
| **flake8** | Linting | `flake8 .` |
| **mypy** | Vérification de types | `mypy .` |
| **pylint** | Analyse de code | `pylint lib` |
| **isort** | Tri des imports | `isort .` |
| **bandit** | Audit de sécurité | `bandit -r lib` |
| **pre-commit** | Hooks Git automatiques | `pre-commit run --all-files` |
| **ipython** | REPL interactif | `ipython` |
| **ipdb** | Débogueur | `import ipdb; ipdb.set_trace()` |

## Tests

### Exécuter les Tests

**Tous les tests:**
```bash
pytest
```

**Tests avec couverture:**
```bash
pytest --cov=lib --cov-report=html
```

**Tests spécifiques:**
```bash
pytest tests/test_example.py
pytest tests/test_example.py::TestExample::test_basic_assertion
```

**Exclure les tests lents:**
```bash
pytest -m "not slow"
```

**Tests par catégorie:**
```bash
pytest -m unit           # Tests unitaires
pytest -m integration    # Tests d'intégration
pytest -m gpu            # Tests nécessitant GPU
```

**Tests en parallèle:**
```bash
pytest -n auto  # Utilise tous les cœurs CPU
```

### Structure des Tests

```
tests/
├── __init__.py          # Package de tests
├── conftest.py          # Fixtures et configuration
├── test_example.py      # Tests d'exemple
└── unit/                # Tests unitaires (à créer)
    └── test_*.py
```

### Écrire des Tests

```python
import pytest
from pathlib import Path

class TestMyFeature:
    """Test my feature"""

    def test_basic(self):
        """Test basic functionality"""
        assert True

    @pytest.mark.slow
    def test_slow_operation(self):
        """Slow test - skip with -m 'not slow'"""
        pass

    def test_with_fixture(self, temp_dir: Path):
        """Test using a fixture"""
        assert temp_dir.exists()
```

## Linting et Formatage

### Formater le Code

**Black (formatage automatique):**
```bash
black .
black lib/  # Formater un dossier spécifique
black app.py  # Formater un fichier
```

**isort (trier les imports):**
```bash
isort .
```

### Vérifier le Code

**Flake8 (style):**
```bash
flake8 .
flake8 lib/
```

**MyPy (types):**
```bash
mypy .
mypy lib/
```

**Pylint (analyse complète):**
```bash
pylint lib
pylint app.py
```

**Bandit (sécurité):**
```bash
bandit -r lib
```

### Pre-commit Hooks

**Installer les hooks:**
```bash
pre-commit install
```

**Exécuter manuellement:**
```bash
pre-commit run --all-files
```

**Les hooks s'exécutent automatiquement avant chaque commit et vérifient:**
- Formatage (black, isort)
- Linting (flake8)
- Types (mypy)
- Sécurité (bandit, safety)
- Fichiers (trailing whitespace, EOF, etc.)

## Workflow de Développement

### 1. Créer une Branche

```bash
git checkout -b feature/ma-nouvelle-fonctionnalite
```

### 2. Développer

```bash
# Éditer le code dans VSCode
# Les extensions Python sont configurées automatiquement

# Tester en continu
pytest --watch  # Nécessite pytest-watch

# Formater automatiquement
# (Activé par défaut dans VSCode: formatOnSave)
```

### 3. Vérifier la Qualité

```bash
# Formater
black .
isort .

# Vérifier
flake8 .
mypy .
pylint lib

# Tester
pytest --cov=lib

# Hooks pre-commit
pre-commit run --all-files
```

### 4. Commit

```bash
# Les pre-commit hooks s'exécutent automatiquement
git add .
git commit -m "feat: ma nouvelle fonctionnalité"
```

### 5. Push

```bash
git push origin feature/ma-nouvelle-fonctionnalite
```

## Commandes Utiles

### Application

**Démarrer l'application:**
```bash
python app.py
```

**Mode headless (CLI):**
```bash
python app.py --headless \
  --ebook ebooks/test.epub \
  --tts-engine xtts \
  --output-dir audiobooks/cli
```

### Environnement

**Installer les dépendances:**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

**Mode éditable:**
```bash
pip install -e .
```

**Mettre à jour les dépendances:**
```bash
pip install --upgrade -r requirements-dev.txt
```

### Docker

**Reconstruire le container:**
```bash
docker-compose -f docker-compose.dev.yml build --no-cache
```

**Voir les logs:**
```bash
docker-compose -f docker-compose.dev.yml logs -f
```

**Nettoyer:**
```bash
docker-compose -f docker-compose.dev.yml down -v
```

## Configuration VSCode

Le Dev Container configure automatiquement:

### Extensions Installées
- Python
- Pylance
- Black Formatter
- Flake8
- MyPy
- Pylint
- Docker
- GitLens
- YAML
- Markdown

### Paramètres
- Formatage automatique à la sauvegarde
- Linting activé
- Tests pytest configurés
- Type checking avec Pylance
- Rulers à 88 et 120 caractères

## Dépannage

### Le container ne démarre pas

**Vérifier Docker:**
```bash
docker --version
docker-compose --version
```

**Voir les logs:**
```bash
docker-compose -f docker-compose.dev.yml logs
```

### Problèmes de permissions

**Si les fichiers sont en root:**
```bash
sudo chown -R $USER:$USER .
```

### GPU non détecté

**Vérifier NVIDIA Runtime:**
```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

**Si erreur, installer nvidia-docker:**
```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

### Dépendances manquantes

**Réinstaller:**
```bash
# Dans le container
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .
```

### Pre-commit hooks échouent

**Mettre à jour les hooks:**
```bash
pre-commit clean
pre-commit install
pre-commit autoupdate
```

**Passer les hooks temporairement:**
```bash
git commit --no-verify
```

## Ressources

- [Documentation Docker](https://docs.docker.com/)
- [VSCode Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers)
- [pytest Documentation](https://docs.pytest.org/)
- [Black Documentation](https://black.readthedocs.io/)
- [Pre-commit Documentation](https://pre-commit.com/)

## Support

Pour toute question ou problème:
1. Vérifiez les issues GitHub existantes
2. Consultez la documentation du projet
3. Créez une nouvelle issue avec les détails du problème

---

**Happy Coding! 🚀**
