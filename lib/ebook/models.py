"""
EPUB Models Module
Defines data structures for EPUB handling.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class EbookMetadata:
    """
    Represents metadata extracted from an ebook.
    """
    title: Optional[str] = None
    creator: Optional[str] = None  # Author
    contributor: Optional[str] = None
    language: Optional[str] = None
    identifier: Optional[str] = None  # ISBN, etc.
    publisher: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None  # Genre, keywords
    rights: Optional[str] = None  # Copyright
    format: Optional[str] = None
    type: Optional[str] = None
    coverage: Optional[str] = None
    relation: Optional[str] = None
    source: Optional[str] = None
    modified: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            'title': self.title,
            'creator': self.creator,
            'contributor': self.contributor,
            'language': self.language,
            'identifier': self.identifier,
            'publisher': self.publisher,
            'date': self.date,
            'description': self.description,
            'subject': self.subject,
            'rights': self.rights,
            'format': self.format,
            'type': self.type,
            'coverage': self.coverage,
            'relation': self.relation,
            'source': self.source,
            'modified': self.modified
        }


@dataclass
class Chapter:
    """
    Represents a single chapter in an ebook.
    """
    index: int
    title: Optional[str] = None
    sentences: List[str] = field(default_factory=list)
    duration: float = 0.0  # Audio duration in seconds
    audio_path: Optional[str] = None

    def __len__(self) -> int:
        """Return number of sentences in the chapter."""
        return len(self.sentences)

    def add_sentence(self, sentence: str):
        """Add a sentence to the chapter."""
        if sentence and sentence.strip():
            self.sentences.append(sentence.strip())


@dataclass
class Ebook:
    """
    Represents an ebook with its metadata and content.
    """
    file_path: str
    format: str  # epub, pdf, mobi, etc.
    metadata: EbookMetadata = field(default_factory=EbookMetadata)
    toc: List[str] = field(default_factory=list)  # Table of Contents
    chapters: List[Chapter] = field(default_factory=list)
    cover_path: Optional[str] = None

    def __len__(self) -> int:
        """Return number of chapters."""
        return len(self.chapters)

    def get_total_sentences(self) -> int:
        """Calculate total number of sentences across all chapters."""
        return sum(len(chapter) for chapter in self.chapters)
