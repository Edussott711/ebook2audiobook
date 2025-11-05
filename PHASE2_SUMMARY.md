# Phase 2 - Modules Métier (Partiellement Complété)

## ✅ Modules Implémentés

### 1. lib/ebook/ - Manipulation EPUB (COMPLET)

#### converter.py
- `convert2epub()` - Conversion de formats variés vers EPUB
- Support PDF avec traitement spécial (Markdown)
- Intégration Calibre (ebook-convert)

#### extractor.py
- `get_cover()` - Extraction de la couverture
- `get_chapters()` - Extraction et traitement des chapitres

#### metadata.py
- `get_ebook_title()` - Extraction du titre (3 méthodes de fallback)
- `extract_toc()` - Table des matières
- `get_all_spine_documents()` - Documents dans l'ordre de lecture

#### models.py
- `EbookMetadata` - Dataclass pour métadonnées
- `Chapter` - Dataclass pour chapitres
- `Ebook` - Dataclass pour ebook complet

### 2. lib/text/ - Traitement de Texte (PARTIEL)

#### normalizer.py (COMPLET)
- `normalize_text()` - Normalisation complète pour TTS
- `filter_sml()` - Filtrage des tags SML (Speech Markup Language)

#### number_converter.py (COMPLET)
- `roman2number()` - Conversion chiffres romains
- `number_to_words()` - Nombres → mots (num2words)

#### utils.py (COMPLET)
- `get_num2words_compat()` - Test compatibilité num2words par langue

#### processor.py (PLACEHOLDER)
- `filter_chapter()` - Traitement avancé de chapitres (référence temporaire à lib.functions)
- ⚠️ À implémenter : extraction complète de la fonction monolithique (237 lignes)

#### tokenizers/ (PLACEHOLDER)
- Structure créée pour tokenizers par langue
- ⚠️ À implémenter : jieba (chinois), sudachi (japonais), soynlp (coréen), pythainlp (thaï)

### 3. lib/audio/ - Traitement Audio (PLACEHOLDERS)

#### converter.py (PLACEHOLDER)
- `convert_chapters2audio()` - Conversion chapitres → audio TTS
- ⚠️ Référence temporaire à lib.functions

#### combiner.py (PLACEHOLDER)
- `combine_audio_sentences()` - Combinaison phrases audio
- `assemble_chunks()` - Assemblage FFmpeg
- ⚠️ Références temporaires à lib.functions

#### exporter.py (PLACEHOLDER)
- `combine_audio_chapters()` - Export final multi-format (AAC, MP3, M4B, etc.)
- ⚠️ Référence temporaire à lib.functions

## 📊 État d'avancement

| Module | Implémentation | Tests | Documentation |
|--------|----------------|-------|---------------|
| lib/ebook/ | ✅ 100% | ❌ 0% | ✅ Docstrings |
| lib/text/normalizer | ✅ 100% | ❌ 0% | ✅ Docstrings |
| lib/text/number_converter | ✅ 100% | ❌ 0% | ✅ Docstrings |
| lib/text/processor | ⚠️ Placeholder | ❌ 0% | ✅ Docstrings |
| lib/text/tokenizers | ⚠️ Placeholder | ❌ 0% | ✅ Docstrings |
| lib/audio/ | ⚠️ Placeholders | ❌ 0% | ✅ Docstrings |

## 🔄 Compatibilité Rétroactive

Tous les placeholders utilisent des **imports temporaires** depuis `lib.functions` pour maintenir la compatibilité pendant la migration :

```python
# Exemple de placeholder compatible
def filter_chapter(doc, lang, lang_iso1, tts_engine, stanza_nlp, is_num2words_compat):
    from lib.functions import filter_chapter as original_filter_chapter
    return original_filter_chapter(doc, lang, lang_iso1, tts_engine, stanza_nlp, is_num2words_compat)
```

## 🚀 Prochaines Étapes (Phase 2.1)

### Priorité HAUTE
1. **Implémenter lib/text/processor.py** - Extraction complète de filter_chapter()
2. **Implémenter lib/audio/converter.py** - Extraction de convert_chapters2audio()
3. **Implémenter lib/audio/combiner.py** - Extraction de combine_audio_sentences()
4. **Implémenter lib/audio/exporter.py** - Extraction de combine_audio_chapters()

### Priorité MOYENNE
5. **Créer lib/text/sentence_splitter.py** - Extraction de get_sentences()
6. **Implémenter lib/text/tokenizers/** - Tokenizers par langue
7. **Créer lib/text/date_converter.py** - Conversion dates/heures
8. **Créer lib/text/math_converter.py** - Conversion symboles mathématiques

### Priorité BASSE
9. Créer lib/core/conversion/ - Orchestration
10. Créer lib/ui/ - Interface Gradio refactorisée

## ✅ Bénéfices Actuels

Même avec des placeholders, la Phase 2 apporte :

1. **Structure claire** - Organisation par domaine métier
2. **Documentation** - Docstrings complètes pour tous les modules
3. **Isolation** - Modules EPUB et normalisation entièrement indépendants
4. **Compatibilité** - Code existant continue de fonctionner
5. **Extensibilité** - Facile d'ajouter de nouvelles implémentations

## 📝 Notes de Migration

Pour utiliser les nouveaux modules :

```python
# Au lieu de :
from lib.functions import convert2epub, get_chapters, get_cover, normalize_text

# Utiliser :
from lib.ebook import convert2epub, get_chapters, get_cover
from lib.text import normalize_text, filter_sml, roman2number
```

Les fonctions avec placeholders (filter_chapter, convert_chapters2audio, etc.) fonctionnent **exactement comme avant** via les imports temporaires.
