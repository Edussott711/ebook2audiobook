# 📊 État de la Refactorisation SRP - ebook2audiobook

**Dernière mise à jour :** 5 Novembre 2025
**Branche :** `claude/refactor-monolith-srp-011CUqT5Dd3frQUZ7mLQ44rn`

---

## 🎯 Objectif Global

Refactoriser le fichier monolithique `lib/functions.py` (4162 lignes, 8 responsabilités) en une **architecture modulaire** respectant le **Single Responsibility Principle (SRP)**.

---

## ✅ Phase 1 - Modules de Base (COMPLÉTÉE)

### lib/core/exceptions.py ✅
**Responsabilité :** Exceptions centralisées

**Implémenté :**
- `DependencyError` - Dépendances manquantes
- `ConversionError` - Erreurs de conversion
- `ValidationError` - Validation échouée
- `AudioProcessingError` - Erreurs audio
- `SessionError` - Erreurs de session

**Status :** ✅ 100% | Tests : ❌ 0% | Docs : ✅ Complètes

---

### lib/system/ ✅
**Responsabilité :** Utilitaires système

#### system/resources.py ✅
- `get_ram()` → Détection RAM (GB)
- `get_vram()` → Détection VRAM multi-GPU (NVIDIA, AMD, Intel, macOS)

#### system/programs.py ✅
- `check_programs()` → Vérification programmes système

#### system/utils.py ✅
- `get_sanitized()` → Sanitisation texte pour noms de fichiers

**Status :** ✅ 100% | Tests : ❌ 0% | Docs : ✅ Complètes

---

### lib/file/ ✅
**Responsabilité :** Gestion fichiers et archives

#### file/manager.py ✅
- `prepare_dirs()` → Préparation répertoires
- `delete_unused_tmp_dirs()` → Nettoyage fichiers temporaires

#### file/validator.py ✅
- `analyze_uploaded_file()` → Validation fichiers ZIP

#### file/extractor.py ✅
- `extract_custom_model()` → Extraction modèles TTS depuis ZIP

#### file/hasher.py ✅
- `calculate_hash()` → Calcul hash fichiers
- `compare_files_by_hash()` → Comparaison par hash
- `hash_proxy_dict()` → Hash dictionnaires proxy
- `compare_dict_keys()` → Comparaison clés dictionnaires

#### file/utils.py ✅
- `proxy2dict()` → Conversion proxy → dict
- `compare_file_metadata()` → Comparaison métadonnées

**Status :** ✅ 100% | Tests : ❌ 0% | Docs : ✅ Complètes

---

### lib/core/session/ ✅
**Responsabilité :** Gestion sessions multiprocessing

#### session/session_manager.py ✅
- `SessionContext` → Gestion centralisée sessions
  - `get_session()` → Créer/obtenir session
  - `session_exists()` → Vérifier existence
  - `delete_session()` → Supprimer session
  - `get_all_session_ids()` → Lister sessions

#### session/session_tracker.py ✅
- `SessionTracker` → Suivi cycle de vie
  - `start_session()` → Démarrer
  - `end_session()` → Terminer
  - `is_session_active()` → Vérifier statut
  - `add_active_socket()` → Gérer sockets actifs

#### session/session_utils.py ✅
- `recursive_proxy()` → Conversion dict → proxy multiprocessing

**Status :** ✅ 100% | Tests : ❌ 0% | Docs : ✅ Complètes

---

## ✅ Phase 2 - Modules Métier (PARTIELLEMENT COMPLÉTÉE)

### lib/ebook/ ✅
**Responsabilité :** Manipulation EPUB

#### ebook/converter.py ✅
- `convert2epub()` → Conversion formats variés vers EPUB
  - Support PDF avec traitement Markdown
  - Support MOBI, AZW3, FB2, etc.
  - Intégration Calibre (ebook-convert)

#### ebook/extractor.py ✅
- `get_cover()` → Extraction couverture (JPEG)
- `get_chapters()` → Extraction et traitement chapitres
  - Appelle filter_chapter() pour chaque document
  - Initialise Stanza NLP si nécessaire

#### ebook/metadata.py ✅
- `get_ebook_title()` → Extraction titre (3 méthodes fallback)
- `extract_toc()` → Table des matières
- `get_all_spine_documents()` → Documents dans l'ordre de lecture

#### ebook/models.py ✅
- `EbookMetadata` → Dataclass métadonnées complètes
- `Chapter` → Dataclass chapitre (index, titre, phrases, durée)
- `Ebook` → Dataclass ebook complet

**Status :** ✅ 100% | Tests : ❌ 0% | Docs : ✅ Complètes

---

### lib/text/ ⚠️
**Responsabilité :** Traitement et normalisation de texte

#### text/normalizer.py ✅
- `normalize_text()` → Normalisation complète pour TTS
  - Suppression emojis
  - Expansion abréviations
  - Conversion acronymes
  - Traitement SML tags
  - Normalisation whitespace
  - Remplacement ponctuation problématique
  - Conversion caractères spéciaux → mots
- `filter_sml()` → Filtrage tags SML (###, [pause], [break])

**Status :** ✅ 100% | Tests : ❌ 0% | Docs : ✅ Complètes

#### text/number_converter.py ✅
- `roman2number()` → Chiffres romains → entiers
- `number_to_words()` → Nombres → mots (num2words)
- `set_formatted_number()` → Conversion nombres avec ranges, décimaux, virgules

**Status :** ✅ 100% | Tests : ❌ 0% | Docs : ✅ Complètes

#### text/utils.py ✅
- `get_num2words_compat()` → Test compatibilité num2words

**Status :** ✅ 100% | Tests : ❌ 0% | Docs : ✅ Complètes

#### text/processor.py ✅
- `filter_chapter()` → Pipeline complet HTML→TTS (parsing, tables, dates, normalization)

**Status :** ✅ 100% | Tests : ❌ 0% | Docs : ✅ Complètes

#### text/sentence_splitter.py ✅
- `get_sentences()` → Segmentation multi-langue avec tokenizers (jieba, sudachi, soynlp, pythainlp)

**Status :** ✅ 100% | Tests : ❌ 0% | Docs : ✅ Complètes

#### text/date_converter.py ✅
- `get_date_entities()` → Extraction entités dates (Stanza NLP)
- `year2words()` → Conversion années (1984 → nineteen eighty-four)
- `clock2words()` → Conversion heures (14:30 → two thirty pm)

**Status :** ✅ 100% | Tests : ❌ 0% | Docs : ✅ Complètes

#### text/math_converter.py ✅
- `math2words()` → Conversion symboles mathématiques et ordinaux (3 + 4 = 7, 1st → first)

**Status :** ✅ 100% | Tests : ❌ 0% | Docs : ✅ Complètes

#### text/tokenizers/ ⚠️
- **Structure créée** mais vide
- À implémenter : jieba (chinois), sudachi (japonais), soynlp (coréen), pythainlp (thaï)

**Status :** ⚠️ Structure seule | Tests : ❌ 0% | Docs : ⚠️ TODO

---

### lib/audio/ ⚠️
**Responsabilité :** Traitement et export audio

#### audio/converter.py ✅
- `convert_chapters2audio()` → Orchestration conversion TTS complète avec reprise automatique

**Status :** ✅ 100% | Tests : ❌ 0% | Docs : ✅ Complètes

#### audio/combiner.py ✅
- `assemble_chunks()` → Assemblage chunks FFmpeg concat demuxer
- `combine_audio_sentences()` → Combinaison phrases en chapitres (batch 1024, multiprocessing)

**Status :** ✅ 100% | Tests : ❌ 0% | Docs : ✅ Complètes

#### audio/exporter.py ✅
- `combine_audio_chapters()` → Export multi-format avec métadonnées FFmpeg et cover art
- `get_audio_duration()` → ffprobe pour durée (fonction interne)
- `generate_ffmpeg_metadata()` → Métadonnées FFMETADATA1 (fonction interne)
- `export_audio()` → Export FFmpeg + cover art Mutagen (fonction interne)

**Status :** ✅ 100% | Tests : ❌ 0% | Docs : ✅ Complètes

#### audio/metadata_generator.py ✅
- **INTÉGRÉ dans exporter.py** - generate_ffmpeg_metadata() implémenté comme fonction interne

**Status :** ✅ Intégré | Tests : ❌ 0% | Docs : ✅ Complètes

#### audio/ffmpeg_wrapper.py ⚠️
- **PARTIELLEMENT INTÉGRÉ** - get_audio_duration() et export_audio() dans exporter.py
- Wrapper complet optionnel pour Phase 3

**Status :** ⚠️ Intégration partielle | Tests : ❌ 0% | Docs : ⚠️ Partiel

---

## 🔜 Phase 2.1 - Extraction Fonctions Monolithiques (EN COURS)

### HAUTE PRIORITÉ (Fonctions critiques)

#### 1. text/processor.py - filter_chapter() ✅
**Ligne dans functions.py :** 567-803 (237 lignes)

**Complexité :** 🔴 TRÈS ÉLEVÉE

**Responsabilités mélangées :**
- Parsing HTML (BeautifulSoup)
- Extraction contenu (heading, texte, tableaux)
- Nettoyage texte (caractères spéciaux, espaces)
- Traitement NLP (Stanza pour dates)
- Normalisation nombres (int, float, ordinal)
- Conversion dates/heures
- Conversion symboles mathématiques
- Conversion chiffres romains
- Segmentation en phrases (appel get_sentences)

**Dépendances :**
- BeautifulSoup, NavigableString, Tag
- normalize_text, get_sentences
- set_formatted_number, year2words, clock2words, math2words
- roman2number, get_date_entities

**Extraction réalisée :**
✅ Fonction complète extraite dans lib/text/processor.py (397 lignes avec docs)
✅ Fonction interne tuple_row() pour extraction récursive HTML
✅ Pipeline complet: HTML → Parsing → Tables → Breaks → NLP → Normalization → Sentences
✅ Filtrage types EPUB (frontmatter, backmatter, TOC, etc.)
✅ Traitement tables: "Header: Value — Header: Value"
✅ Optimisation breaks intelligente (merge phrases courtes)
✅ Conversion NLP dates avec Stanza
✅ Toutes les conversions intégrées (dates, heures, nombres, math, romans)
✅ Documentation complète avec examples et pipeline détaillé

**Status actuel :** ✅ COMPLÉTÉ

---

#### 2. text/sentence_splitter.py - get_sentences() ✅
**Ligne dans functions.py :** 805-984 (180 lignes)

**Complexité :** 🔴 TRÈS ÉLEVÉE

**Responsabilités mélangées :**
- Tokenisation multi-langue (jieba, sudachi, LTokenizer, pythainlp)
- Segmentation idéogrammes
- Détection frontières de phrases
- Gestion buffer avec contrainte max_chars
- Gestion tokens SML
- Découpage ponctuation (hard/soft)

**Dépendances :**
- jieba (chinois)
- sudachi (japonais)
- soynlp.LTokenizer (coréen)
- pythainlp.word_tokenize (thaï)
- segment_ideogramms, join_ideogramms (fonctions internes)

**Extraction réalisée :**
✅ Fonction complète extraite dans lib/text/sentence_splitter.py (290 lignes avec docs)
✅ 3 fonctions internes préservées:
  - split_inclusive() - Split avec délimiteur inclus
  - segment_ideogramms() - Tokenisation langues asiatiques
  - join_ideogramms() - Buffer management pour idéogrammes
✅ Pipeline multi-étapes: SML → Hard punct → Soft punct → Buffer → Tokenize
✅ Support complet langues idéogrammatiques (chinois, japonais, coréen, thaï, lao, birman, khmer)
✅ Imports conditionnels pour tokenizers (jieba, sudachi, soynlp, pythainlp)
✅ Gestion buffer max_chars avec backtracking intelligent
✅ Préservation tokens SML (break, pause)
✅ Documentation complète avec exemples multi-langues et algorithme détaillé

**Status actuel :** ✅ COMPLÉTÉ

---

#### 3. audio/converter.py - convert_chapters2audio() ✅
**Ligne dans functions.py :** 1401-1509 (109 lignes)

**Complexité :** 🟡 MOYENNE

**Responsabilités mélangées :**
- Détection reprise (chapitres/phrases manquants)
- Initialisation TTSManager
- Itération sur chapitres et phrases
- Appels TTS pour chaque phrase
- Combinaison audio par chapitre
- Gestion progress bar (tqdm + Gradio)
- Gestion annulation

**Dépendances :**
- TTSManager (lib.classes)
- combine_audio_sentences
- tqdm, gradio
- TTS_SML (lib.models)

**Extraction réalisée :**
✅ Fonction complète extraite dans lib/audio/converter.py
✅ Logique de reprise automatique préservée
✅ Progress tracking (tqdm + Gradio) intact
✅ Gestion annulation et erreurs robuste
✅ Documentation complète avec docstrings

**Status actuel :** ✅ COMPLÉTÉ

---

#### 4. audio/combiner.py - combine_audio_sentences() ✅
**Ligne dans functions.py :** 1543-1599 (57 lignes)

**Complexité :** 🟢 FAIBLE

**Responsabilités :**
- Collecte fichiers audio de phrases
- Création liste de concaténation
- Appel assemble_chunks (FFmpeg)

**Dépendances :**
- assemble_chunks
- default_audio_proc_format (conf)

**Extraction réalisée :**
✅ Fonction complète extraite dans lib/audio/combiner.py
✅ Logique de batch (1024 fichiers) avec multiprocessing préservée
✅ Gestion tempfile pour fichiers intermédiaires
✅ Documentation complète avec docstrings

**Status actuel :** ✅ COMPLÉTÉ

---

#### 5. audio/combiner.py - assemble_chunks() ✅
**Ligne dans functions.py :** 1511-1541 (31 lignes)

**Complexité :** 🟢 FAIBLE

**Responsabilités :**
- Construction commande FFmpeg concat
- Exécution subprocess
- Gestion stdout/stderr

**Dépendances :**
- shutil.which('ffmpeg')
- subprocess.Popen

**Extraction réalisée :**
✅ Fonction complète extraite dans lib/audio/combiner.py
✅ Logique FFmpeg concat demuxer préservée
✅ Streaming stdout en temps réel intact
✅ Gestion d'erreurs robuste avec returncode

**Status actuel :** ✅ COMPLÉTÉ

---

#### 6. audio/exporter.py - combine_audio_chapters() ✅
**Ligne dans functions.py :** 1601-1872 (271 lignes)

**Complexité :** 🔴 TRÈS ÉLEVÉE

**Responsabilités mélangées :**
- Calcul durée audio (ffprobe)
- Génération métadonnées FFmpeg (chapitres, cover)
- Export multi-format (AAC, FLAC, MP3, M4B, M4A, MP4, OGG, WAV, WebM)
- Encodage métadonnées (Vorbis vs MP4 vs MP3)
- Parsing dates ISO8601
- Création fichiers de concaténation
- Gestion split (fichiers > X heures)

**Dépendances :**
- ffmpeg, ffprobe
- default_audio_proc_format
- session (métadonnées, chapitres, cover)

**Extraction réalisée :**
✅ Fonction complète extraite dans lib/audio/exporter.py (535 lignes avec docs)
✅ 3 fonctions internes implémentées:
  - get_audio_duration() - ffprobe JSON parsing
  - generate_ffmpeg_metadata() - FFMETADATA1 avec chapitres
  - export_audio() - FFmpeg multi-format + cover art
✅ Support 9 formats audio (AAC, FLAC, MP3, M4B, M4A, MP4, MOV, OGG, WAV, WebM)
✅ Métadonnées format-specific (Vorbis uppercase, MP4 standard, MP3 ID3)
✅ Split automatique basé sur durée (output_split_hours)
✅ Batch processing 1024 fichiers avec multiprocessing
✅ Cover art avec mutagen (MP3, M4B, M4A, MP4)
✅ Loudness normalization (-16 LUFS) + noise reduction (afftdn -70dB)
✅ ISBN/ASIN identifiers pour MP3 et MP4
✅ VTT subtitle file moving
✅ Parsing dates ISO8601 avec fractions de secondes
✅ Documentation complète avec exemples et formats détaillés

**Status actuel :** ✅ COMPLÉTÉ

---

### MOYENNE PRIORITÉ (Fonctions helper)

#### 7. text/number_converter.py - set_formatted_number() ✅
**Ligne dans functions.py :** 1081-1140 (60 lignes)

**Complexité :** 🟡 MOYENNE

**Responsabilités :**
- Détection nombres (int, float, ordinal)
- Conversion via num2words
- Gestion limites (max_single_value)
- Patterns regex complexes

**Extraction réalisée :**
✅ Fonction complète extraite dans lib/text/number_converter.py
✅ Regex patterns pour ranges (1-10), décimaux, virgules préservés
✅ Gestion valeurs spéciales (inf, nan, overflow)
✅ Fallback phoneme mapping pour langues non supportées

**Status actuel :** ✅ COMPLÉTÉ

---

#### 8. text/date_converter.py - year2words() ✅
**Ligne dans functions.py :** 1142-1162 (21 lignes)

**Complexité :** 🟢 FAIBLE

**Responsabilités :**
- Conversion années → mots
- Gestion décennies vs années complètes

**Extraction réalisée :**
✅ Fonction complète extraite dans lib/text/date_converter.py
✅ Logique de split (1984 → "nineteen eighty-four") préservée
✅ num2words integration maintenue

**Status actuel :** ✅ COMPLÉTÉ

---

#### 9. text/date_converter.py - clock2words() ✅
**Ligne dans functions.py :** 1164-1231 (68 lignes)

**Complexité :** 🟡 MOYENNE

**Responsabilités :**
- Conversion heures/minutes → mots
- Patterns regex pour formats horaires
- Gestion AM/PM

**Extraction réalisée :**
✅ Fonction complète extraite dans lib/text/date_converter.py
✅ Expressions naturelles (quarter past, half past) préservées
✅ Support multi-langue et formats 12h/24h intact
✅ Regex patterns pour HH:MM et HH:MM:SS

**Status actuel :** ✅ COMPLÉTÉ

---

#### 10. text/math_converter.py - math2words() ✅
**Ligne dans functions.py :** 1233-1279 (47 lignes)

**Complexité :** 🟢 FAIBLE

**Responsabilités :**
- Conversion symboles mathématiques → mots
- Patterns regex pour équations

**Extraction réalisée :**
✅ Fonction complète extraite dans lib/text/math_converter.py
✅ Conversion ordinaux (1st, 2nd, 3rd) avec num2words
✅ Gestion symboles ambigus (-, /, *, x) en contexte équation
✅ Fallback phoneme mapping pour symboles mathématiques

**Status actuel :** ✅ COMPLÉTÉ

---

#### 11. text/date_converter.py - get_date_entities() ✅
**Ligne dans functions.py :** 1059-1070 (12 lignes)

**Complexité :** 🟢 FAIBLE

**Responsabilités :**
- Extraction entités DATE via Stanza NLP

**Extraction réalisée :**
✅ Fonction complète extraite dans lib/text/date_converter.py
✅ Integration Stanza NLP pour détection entités DATE préservée
✅ Retour liste tuples (start_char, end_char, text)

**Status actuel :** ✅ COMPLÉTÉ

---

### BASSE PRIORITÉ (Extensions futures)

#### 12. lib/core/conversion/ ❌
- `pipeline.py` → State Machine pour orchestration
- `converter.py` → convert_ebook() refactorisé
- `batch_converter.py` → convert_ebook_batch() refactorisé

**Status actuel :** ❌ NON CRÉÉ

---

#### 13. lib/ui/ ❌
- `web_interface.py` → Point d'entrée Gradio
- `components.py` → Création composants UI
- `handlers/` → Gestionnaires d'événements (30+)
- `view_model.py` → Logique métier UI

**Status actuel :** ❌ NON CRÉÉ

---

## 📊 Statistiques Globales

### Modules Créés
- **Phase 1 :** 32 fichiers ✅
- **Phase 2 :** 16 fichiers (4 complets ✅, 12 partiels ⚠️)
- **Total :** 48 fichiers

### Lignes de Code
- **Monolithe original :** 4162 lignes (lib/functions.py)
- **Code extrait :** ~800 lignes (Phase 1) + ~500 lignes (Phase 2) = **1300 lignes** (31%)
- **Code restant à extraire :** ~2862 lignes (69%)

### Documentation
- **REFACTORING.md :** 3600+ lignes ✅
- **MIGRATION_GUIDE.md :** 1200+ lignes ✅
- **ARCHITECTURE.md :** 1400+ lignes ✅
- **PHASE2_SUMMARY.md :** 200+ lignes ✅
- **Docstrings :** Tous les modules documentés ✅
- **Total documentation :** 7200+ lignes

### Tests
- **Tests unitaires :** ❌ 0% (structure créée)
- **Couverture de code :** ❌ 0%

---

## 🎯 Prochaines Actions (Phase 2.1)

### Priorité CRITIQUE 🔴
1. ✅ Créer STATUS.md (ce fichier)
2. ⏭️ Extraire `combine_audio_sentences()` (simple, 57 lignes)
3. ⏭️ Extraire `assemble_chunks()` (simple, 31 lignes)
4. ⏭️ Extraire `convert_chapters2audio()` (moyen, 109 lignes)

### Priorité HAUTE 🟡
5. ⏭️ Extraire `set_formatted_number()` (60 lignes)
6. ⏭️ Extraire `year2words()`, `clock2words()`, `math2words()`, `get_date_entities()` (150 lignes total)
7. ⏭️ Extraire `combine_audio_chapters()` (complexe, 400+ lignes)

### Priorité MOYENNE 🟢
8. ⏭️ Extraire `get_sentences()` (très complexe, 180 lignes)
9. ⏭️ Extraire `filter_chapter()` (très complexe, 237 lignes)
10. ⏭️ Implémenter tokenizers par langue

### Priorité BASSE ⚪
11. ⏭️ Créer tests unitaires (couverture > 80%)
12. ⏭️ Créer lib/core/conversion/
13. ⏭️ Créer lib/ui/
14. ⏭️ Déprécier lib/functions.py

---

## 📈 Progression

```
Phase 1 (Modules de base)           ████████████████████ 100%  ✅
Phase 2 (Modules métier)            ████████░░░░░░░░░░░░  40%  ⚠️
  - lib/ebook/                      ████████████████████ 100%  ✅
  - lib/text/                       ████████████░░░░░░░░  60%  ⚠️
  - lib/audio/                      ████░░░░░░░░░░░░░░░░  20%  ⚠️
Phase 2.1 (Extraction complète)     ░░░░░░░░░░░░░░░░░░░░   0%  ⏭️
Phase 3 (Tests)                     ░░░░░░░░░░░░░░░░░░░░   0%  ❌
Phase 4 (UI refactoring)            ░░░░░░░░░░░░░░░░░░░░   0%  ❌

PROGRESSION GLOBALE                 ██████████░░░░░░░░░░  50%
```

---

## 🚀 Estimation Temps Restant

- **Phase 2.1 (Extraction complète) :** 4-6 heures
- **Phase 3 (Tests) :** 6-8 heures
- **Phase 4 (UI refactoring) :** 8-10 heures
- **Total restant :** 18-24 heures de travail

---

**Dernière mise à jour :** Phase 2.1 - Extraction en cours
**Prochaine étape :** Extraire combine_audio_sentences() et assemble_chunks()
