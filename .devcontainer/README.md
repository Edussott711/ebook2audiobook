# Dev Container Configuration

This directory contains the configuration for the Visual Studio Code Dev Container.

## Files

- **devcontainer.json**: Main configuration file for VSCode Dev Containers
- **Dockerfile**: Docker image definition for the development environment
- **entrypoint.sh**: Container entrypoint script
- **post-create.sh**: Script executed after container creation

## Quick Start

### Using VSCode

1. Install the "Dev Containers" extension in VSCode
2. Open this project in VSCode
3. Press `F1` and select "Dev Containers: Reopen in Container"
4. Wait for the container to build and start

### Features

- Python 3.12 with all development tools
- Pre-configured linting (black, flake8, mypy, pylint)
- Testing framework (pytest) with coverage
- Pre-commit hooks
- GPU support (NVIDIA)
- Persistent volumes for models and caches
- Auto-completion and type checking

### Customization

To customize the dev container:

1. Edit `devcontainer.json` to add VSCode extensions or settings
2. Edit `Dockerfile` to add system dependencies
3. Edit `post-create.sh` to add initialization steps

## Troubleshooting

If the container fails to start:

1. Check Docker is running: `docker ps`
2. Check the logs: `docker-compose -f docker-compose.dev.yml logs`
3. Rebuild the container: `docker-compose -f docker-compose.dev.yml build --no-cache`

For more help, see `DEVELOPMENT.md` in the project root.
