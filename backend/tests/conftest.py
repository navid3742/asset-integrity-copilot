import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['OPENAI_API_KEY']=''
os.environ['DEMO_PASSWORD']=''
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client(tmp_path,monkeypatch):
    from app import db
    monkeypatch.setattr(db,'DATABASE_PATH',tmp_path/'test.sqlite3')
    with TestClient(app) as c:
        yield c
