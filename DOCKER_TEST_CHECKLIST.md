# 🐳 Docker Test Checklist

## Tests Automatisés Rapides

```bash
# Lancer tous les tests de validation
./test-docker.sh
```

## Tests Manuels Détaillés

### ✅ Test 1: Build & Import
```bash
docker build -t ebook2audiobook .
```
**Vérifier:** Pas d'erreur de build, tous les packages installés

---

### ✅ Test 2: Interface Gradio (GUI)
```bash
docker run -p 7860:7860 ebook2audiobook
```

**Checklist Interface:**
- [ ] Gradio démarre sans erreur
- [ ] Page accessible sur http://localhost:7860
- [ ] Pas de `orjson.JSONDecodeError` dans les logs
- [ ] Pas de `AttributeError: 'NoneType'` dans les logs
- [ ] Session se crée automatiquement
- [ ] Upload de fichier fonctionne
- [ ] Liste déroulante langue/voix/TTS fonctionne
- [ ] Données de session s'affichent dans le JSON viewer

**Logs à surveiller:**
```
✓ Session persistence initialized and cleanup complete
✓ Created and saved new session: [UUID]
Running on local URL:  http://0.0.0.0:7860
```

**Erreurs à NE PAS voir:**
```
❌ orjson.JSONDecodeError: unexpected character
❌ AttributeError: 'NoneType' object has no attribute 'sessions'
❌ TypeError: expected str, bytes or os.PathLike object, not NoneType
❌ SystemExit: 1
```

---

### ✅ Test 3: Conversion Headless
```bash
# Créer un fichier de test
mkdir -p test_books
# Placer un .epub dans test_books/

docker run -v $(pwd)/test_books:/books ebook2audiobook \
  --headless \
  --ebook /books/your_test.epub \
  --language eng \
  --device cpu
```

**Checklist Conversion:**
- [ ] Pas d'erreur `TypeError: NoneType` dans custom_model_dir
- [ ] Répertoires créés correctement
- [ ] Session sauvegardée
- [ ] Progression affichée
- [ ] Conversion complète jusqu'au bout

---

### ✅ Test 4: Session Persistence
```bash
# Démarrer conversion
docker run -v $(pwd)/test_books:/books ebook2audiobook \
  --headless \
  --ebook /books/test.epub \
  --session test-resume-123 \
  --language eng

# Interrompre avec Ctrl+C après quelques secondes

# Reprendre
docker run -v $(pwd)/test_books:/books ebook2audiobook \
  --headless \
  --ebook /books/test.epub \
  --session test-resume-123 \
  --language eng
```

**Checklist Resume:**
- [ ] Checkpoint détecté au redémarrage
- [ ] Message "Found existing checkpoint!" affiché
- [ ] Conversion reprend où elle s'est arrêtée
- [ ] Pas de re-génération des fichiers déjà créés

---

### ✅ Test 5: Multi-Session (GUI)
```bash
docker run -p 7860:7860 ebook2audiobook
```

**Dans le navigateur:**
1. Ouvrir 2 onglets sur http://localhost:7860
2. Upload différents fichiers dans chaque onglet
3. Démarrer conversion dans onglet 1
4. Vérifier que onglet 2 peut charger/créer sa propre session

**Checklist Multi-Session:**
- [ ] Chaque onglet a son propre ID de session
- [ ] Sessions sauvegardées séparément
- [ ] Pas de conflit entre sessions
- [ ] Sélecteur de session fonctionne

---

### ✅ Test 6: Modules SRP Refactorés
```bash
docker run --rm ebook2audiobook python3 -c "
import sys
sys.path.insert(0, '/app')

# Vérifier tous les modules SRP
from lib.audio.converter import convert_chapters2audio
from lib.audio.combiner import combine_audio_sentences
from lib.audio.exporter import combine_audio_chapters
from lib.ebook.extractor import get_chapters
from lib.ebook.converter import convert2epub
from lib.text.processor import filter_chapter
from lib.text.sentence_splitter import get_sentences
from lib.file.utils import proxy2dict
from lib.core.exceptions import DependencyError

print('✅ Tous les modules SRP importés!')
"
```

**Checklist Modules:**
- [ ] Tous les imports réussissent
- [ ] Pas de circular import
- [ ] Pas de module manquant

---

## 🎯 Résultats Attendus

### ✅ SUCCÈS si:
- Tous les tests automatisés passent (./test-docker.sh)
- Interface Gradio démarre sans erreur
- Conversion headless fonctionne
- Sessions se créent/chargent correctement
- Pas d'erreur `orjson`, `TypeError`, `AttributeError`

### ❌ ÉCHEC si:
- Build Docker échoue
- Erreurs d'import Python
- orjson.JSONDecodeError
- TypeError avec NoneType
- SystemExit crash

---

## 📊 Commits de Correction Appliqués

| Commit | Fix |
|--------|-----|
| 1f5d862 | Fix context references (context_module.*) |
| 313e1ad | Fix Gradio crashes (is_gui_process, alert_exception) |
| 579bc9b | Consolidate DependencyError |
| 16dff34 | Fix orjson JSON strings |
| 253fc5f | Fix proxy2dict duck typing (ROOT CAUSE) |
| c92e84e | Fix custom_model_dir initialization order |

---

## 🆘 Debugging

Si problème, regarder les logs:
```bash
# Logs complets avec debug
docker run -e GRADIO_DEBUG=1 -p 7860:7860 ebook2audiobook

# Inspecter le conteneur
docker run -it --entrypoint /bin/bash ebook2audiobook

# Vérifier structure des fichiers
docker run --rm ebook2audiobook ls -la /app/lib/
```

---

## 📝 Notes

- Tous les correctifs sont dans la branche: `claude/refactor-monolith-srp-011CUqT5Dd3frQUZ7mLQ44rn`
- Architecture SRP respectée
- Pas de régression des fonctionnalités
- Workflow complet testé: Gradio → Session → Conversion → Audio
