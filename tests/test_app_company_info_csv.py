import os
import sys
import types
import json
from pathlib import Path
import faiss

# Ensure a dummy FAISS cache exists so build_utility_embeddings loads without error
cache_dir = Path(__file__).resolve().parents[1] / 'data' / 'faiss'
cache_dir.mkdir(parents=True, exist_ok=True)
faiss.write_index(faiss.IndexFlatIP(1), str(cache_dir / 'utility_embeddings.index'))
(cache_dir / 'utility_embeddings.json').write_text(json.dumps([]), encoding='utf-8')

# Record any existing flask module to restore later
_original_flask = sys.modules.get('flask')

# Provide minimal python-dotenv stub if missing
if 'dotenv' not in sys.modules:
    dotenv = types.ModuleType('dotenv')
    dotenv.dotenv_values = lambda *a, **kw: {}
    dotenv.set_key = lambda *a, **kw: None
    sys.modules['dotenv'] = dotenv

# Provide minimal flask stub for testing
flask = types.ModuleType('flask')

class DummyRequest:
    def __init__(self):
        self.form = {}
        self.files = {}
        self.method = 'GET'

request = DummyRequest()

def render_template(name, **ctx):
    render_template.context = ctx
    return ctx

def redirect(url):
    return url

def url_for(name, **kw):
    return f'/{name}'

def flash(msg):
    pass

def send_from_directory(directory, filename, as_attachment=False):
    return os.path.join(directory, filename)

def jsonify(*args, **kwargs):
    if args and not kwargs:
        return args[0] if len(args) == 1 else list(args)
    return kwargs

# Stub session object
session = {}

class DummyFlask:
    def __init__(self, *a, **kw):
        pass
    def route(self, *a, **kw):
        def decorator(f):
            return f
        return decorator

flask.Flask = DummyFlask
flask.render_template = render_template
flask.request = request
flask.redirect = redirect
flask.url_for = url_for
flask.flash = flash
flask.send_from_directory = send_from_directory
flask.jsonify = jsonify
flask.session = session
sys.modules['flask'] = flask

# Ensure app is re-imported under the stubbed flask module
sys.modules.pop('app', None)
from app import run_utility
from utils import common, find_company_info


def test_find_company_info_csv(monkeypatch, tmp_path):
    # Prepare input CSV and set as previous file
    csv_in = tmp_path / 'in.csv'
    csv_in.write_text('organization_name\nFoo\n', encoding='utf-8')
    session['prev_csv_path'] = str(csv_in)

    out_path = tmp_path / 'out.csv'
    monkeypatch.setattr(common, 'make_temp_csv_filename', lambda *_: str(out_path))

    def dummy_from_csv(inp, out):
        with open(out, 'w') as fh:
            fh.write('ok')
    monkeypatch.setattr(find_company_info, 'find_company_info_from_csv', dummy_from_csv)

    request.method = 'POST'
    request.form = {'util_name': 'find_company_info', 'input_mode': 'previous'}
    request.files = {}

    ctx = run_utility()
    assert ctx['download_name'] == str(out_path)
    assert os.path.exists(out_path)

# Restore real flask module so stub does not leak to other tests
if _original_flask is not None:
    sys.modules['flask'] = _original_flask
else:
    sys.modules.pop('flask', None)
    import importlib
    sys.modules['flask'] = importlib.import_module('flask')
# Remove stub-loaded app module so it will be re-imported under real flask
sys.modules.pop('app', None)
