from pathlib import Path


def test_repo_has_core_files():
    root = Path(__file__).resolve().parents[1]
    assert (root / 'memory_recall_guard.py').exists()
    assert (root / 'README.md').exists()
    assert (root / 'pyproject.toml').exists()
