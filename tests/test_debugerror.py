import importlib
from pathlib import Path


def test_import_without_working_directory(monkeypatch):
    debugerror = importlib.import_module("web.debugerror")

    def missing_cwd():
        raise FileNotFoundError("working directory was removed")

    with monkeypatch.context() as patch:
        patch.setattr("os.getcwd", missing_cwd)
        importlib.reload(debugerror)

    assert debugerror.whereami == str(Path(debugerror.__file__).parent)
