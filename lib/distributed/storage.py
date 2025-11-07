"""
Gestionnaire de stockage partagé pour les fichiers audio.
"""

import os
import shutil
import logging
from typing import List
from pathlib import Path

logger = logging.getLogger(__name__)


class SharedStorageHandler:
    """
    Gère le stockage partagé des fichiers audio entre workers.

    Supporte:
    - NFS: Montage réseau partagé
    - S3: Amazon S3 ou compatible (MinIO)
    - Local: Système de fichiers local (dev/test uniquement)
    """

    def __init__(
        self,
        storage_type: str = 'nfs',
        storage_path: str = '/mnt/shared'
    ):
        """
        Args:
            storage_type: 'nfs', 's3', ou 'local'
            storage_path: Chemin de base du stockage
        """
        self.storage_type = storage_type
        self.base_path = storage_path

        if storage_type == 's3':
            self._init_s3()
        elif storage_type in ['nfs', 'local']:
            self._init_filesystem()
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")

        logger.info(f"Storage handler initialized: {storage_type} @ {storage_path}")

    def _init_s3(self):
        """Initialise le client S3."""
        try:
            import boto3
            self.s3_client = boto3.client(
                's3',
                endpoint_url=os.getenv('S3_ENDPOINT_URL'),
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            self.bucket_name = os.getenv('S3_BUCKET_NAME', 'ebook2audiobook')
        except ImportError:
            raise ImportError("boto3 is required for S3 storage. Install with: pip install boto3")

    def _init_filesystem(self):
        """Initialise le système de fichiers."""
        Path(self.base_path).mkdir(parents=True, exist_ok=True)

    def upload_audio(
        self,
        local_path: str,
        session_id: str,
        filename: str
    ) -> str:
        """
        Upload un fichier audio vers le stockage partagé.

        Args:
            local_path: Chemin local du fichier
            session_id: ID de session
            filename: Nom du fichier (sans extension)

        Returns:
            Chemin dans le stockage partagé
        """
        if self.storage_type == 's3':
            return self._upload_to_s3(local_path, session_id, filename)
        else:
            return self._upload_to_filesystem(local_path, session_id, filename)

    def _upload_to_filesystem(
        self,
        local_path: str,
        session_id: str,
        filename: str
    ) -> str:
        """Upload vers NFS ou local filesystem."""
        # Créer répertoire session
        session_dir = Path(self.base_path) / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Chemin de destination
        ext = Path(local_path).suffix
        dest_path = session_dir / f"{filename}{ext}"

        # Copier le fichier
        shutil.copy2(local_path, dest_path)

        logger.debug(f"Uploaded {local_path} -> {dest_path}")
        return str(dest_path)

    def _upload_to_s3(
        self,
        local_path: str,
        session_id: str,
        filename: str
    ) -> str:
        """Upload vers S3."""
        ext = Path(local_path).suffix
        s3_key = f"{session_id}/{filename}{ext}"

        self.s3_client.upload_file(
            local_path,
            self.bucket_name,
            s3_key
        )

        logger.debug(f"Uploaded {local_path} -> s3://{self.bucket_name}/{s3_key}")
        return f"s3://{self.bucket_name}/{s3_key}"

    def download_audio(self, shared_path: str, local_path: str):
        """
        Télécharge un fichier depuis le stockage partagé.

        Args:
            shared_path: Chemin dans le stockage partagé
            local_path: Chemin local de destination
        """
        if shared_path.startswith('s3://'):
            self._download_from_s3(shared_path, local_path)
        else:
            self._download_from_filesystem(shared_path, local_path)

    def _download_from_filesystem(self, shared_path: str, local_path: str):
        """Download depuis filesystem."""
        shutil.copy2(shared_path, local_path)

    def _download_from_s3(self, s3_path: str, local_path: str):
        """Download depuis S3."""
        # Parse s3://bucket/key
        s3_path = s3_path.replace('s3://', '')
        bucket, key = s3_path.split('/', 1)

        self.s3_client.download_file(bucket, key, local_path)

    def list_session_files(self, session_id: str) -> List[str]:
        """
        Liste tous les fichiers d'une session.

        Args:
            session_id: ID de session

        Returns:
            Liste des chemins des fichiers
        """
        if self.storage_type == 's3':
            return self._list_s3_files(session_id)
        else:
            return self._list_filesystem_files(session_id)

    def _list_filesystem_files(self, session_id: str) -> List[str]:
        """Liste les fichiers filesystem."""
        session_dir = Path(self.base_path) / session_id
        if not session_dir.exists():
            return []

        return [str(f) for f in session_dir.glob('*') if f.is_file()]

    def _list_s3_files(self, session_id: str) -> List[str]:
        """Liste les fichiers S3."""
        response = self.s3_client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=f"{session_id}/"
        )

        files = []
        for obj in response.get('Contents', []):
            files.append(f"s3://{self.bucket_name}/{obj['Key']}")

        return files

    def cleanup_session(self, session_id: str):
        """
        Supprime tous les fichiers d'une session.

        Args:
            session_id: ID de session à nettoyer
        """
        if self.storage_type == 's3':
            self._cleanup_s3_session(session_id)
        else:
            self._cleanup_filesystem_session(session_id)

        logger.info(f"Cleaned up session {session_id}")

    def _cleanup_filesystem_session(self, session_id: str):
        """Cleanup filesystem."""
        session_dir = Path(self.base_path) / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir)

    def _cleanup_s3_session(self, session_id: str):
        """Cleanup S3."""
        # Lister et supprimer tous les objets
        objects = self._list_s3_files(session_id)
        for obj_path in objects:
            key = obj_path.replace(f's3://{self.bucket_name}/', '')
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
