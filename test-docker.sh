#!/bin/bash
# Script de test Docker pour ebook2audiobook
# Utilisation: ./test-docker.sh

set -e  # Arrêter en cas d'erreur

echo "🐳 Test 1/4 - Build de l'image..."
docker build -t ebook2audiobook . || {
    echo "❌ Build failed!"
    exit 1
}
echo "✅ Build OK"

echo ""
echo "🐳 Test 2/4 - Test import Python..."
docker run --rm ebook2audiobook python3 -c "
import sys
sys.path.insert(0, '/app')

# Test imports critiques
from lib import context, is_gui_process, active_sessions
from lib.functions import SessionContext, convert_ebook, web_interface
from lib.audio.converter import convert_chapters2audio
from lib.ebook.extractor import get_chapters
from lib.file.utils import proxy2dict
from lib.core.exceptions import DependencyError

print('✅ Tous les imports fonctionnent!')
" || {
    echo "❌ Import test failed!"
    exit 1
}
echo "✅ Imports OK"

echo ""
echo "🐳 Test 3/4 - Test proxy2dict (fix orjson)..."
docker run --rm ebook2audiobook python3 -c "
import sys
sys.path.insert(0, '/app')
from multiprocessing import Manager
from lib.file.utils import proxy2dict

# Test avec DictProxy
manager = Manager()
proxy_dict = manager.dict({'key': 'value', 'nested': {'a': 1}})
result = proxy2dict(proxy_dict)

assert isinstance(result, dict), 'Result should be dict'
assert result['key'] == 'value', 'Value mismatch'
assert isinstance(result['nested'], dict), 'Nested should be dict'

print('✅ proxy2dict gère correctement DictProxy!')
" || {
    echo "❌ proxy2dict test failed!"
    exit 1
}
echo "✅ proxy2dict OK"

echo ""
echo "🐳 Test 4/4 - Test SessionContext..."
docker run --rm ebook2audiobook python3 -c "
import sys
sys.path.insert(0, '/app')
from lib.functions import SessionContext
from lib.file.utils import proxy2dict

# Test création session
ctx = SessionContext()
session = ctx.get_session('test-123')

# Vérifier champs initialisés
assert session['id'] == 'test-123', 'ID mismatch'
assert session['custom_model_dir'] is None, 'Should be None by default'
assert session['voice_dir'] is None, 'Should be None by default'

# Test conversion proxy2dict
session_dict = proxy2dict(session)
assert isinstance(session_dict, dict), 'Should convert to dict'
assert 'id' in session_dict, 'Should have id field'

print('✅ SessionContext fonctionne!')
" || {
    echo "❌ SessionContext test failed!"
    exit 1
}
echo "✅ SessionContext OK"

echo ""
echo "========================================="
echo "🎉 TOUS LES TESTS PASSENT!"
echo "========================================="
echo ""
echo "Lancer l'application:"
echo "  GUI:      docker run -p 7860:7860 ebook2audiobook"
echo "  Headless: docker run -v /books:/books ebook2audiobook --headless --ebook /books/test.epub"
echo ""
