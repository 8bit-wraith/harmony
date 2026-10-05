"""Isolated native resolver regression tests; no vocabulary download or extension build.

Compile the actual Rust resolver, with only its error type stubbed. Full package
pytest remains a separate integration check.
"""
import os
from pathlib import Path
import subprocess

import pytest


@pytest.fixture(scope="module")
def resolver(tmp_path_factory):
    root = Path(__file__).resolve().parents[1]
    source = (root / "src/tiktoken_ext/public_encodings.rs").read_text()
    function = source[source.index("fn resolve_cache_dir()"):source.index("fn resolve_cache_path(")]
    folder = tmp_path_factory.mktemp("native-resolver")
    rust = folder / "resolver.rs"
    rust.write_text('use std::path::PathBuf;\n'
                    '#[derive(Debug)] enum RemoteVocabFileError { IOError(String, std::io::Error) }\n'
                    + function + '\nfn main() { match resolve_cache_dir() { '
                    'Ok(path) => { println!("{}", path.display()); '
                    'assert!(path.is_dir(), "cache directory must exist"); }, '
                    'Err(e) => { eprintln!("{:?}", e); std::process::exit(2); } } }')
    executable = folder / "resolver"
    subprocess.run(["rustc", "--edition", "2021", str(rust), "-o", str(executable)],
                   check=True, capture_output=True, timeout=30)
    return executable


def run(resolver, path):
    env = dict(os.environ, TIKTOKEN_RS_CACHE_DIR=str(path))
    return subprocess.run([str(resolver)], env=env, capture_output=True, text=True, timeout=10)


def test_creates_nested_override(resolver, tmp_path):
    cache = tmp_path / "new" / "cache"
    result = run(resolver, cache)
    assert result.returncode == 0, result.stderr
    assert cache.is_dir()


def test_preserves_existing_cache(resolver, tmp_path):
    sentinel = tmp_path / "existing-vocab"
    sentinel.write_bytes(b"synthetic vocabulary")
    assert run(resolver, tmp_path).returncode == 0
    assert sentinel.read_bytes() == b"synthetic vocabulary"


def test_rejects_file_as_directory(resolver, tmp_path):
    cache = tmp_path / "not-directory"
    cache.write_bytes(b"preserve")
    result = run(resolver, cache)
    assert result.returncode == 2
    assert "creating cache dir" in result.stderr
    assert cache.read_bytes() == b"preserve"


def test_default_cache_uses_temporary_root(resolver, tmp_path):
    env = dict(os.environ, TMPDIR=str(tmp_path), TEMP=str(tmp_path), TMP=str(tmp_path))
    env.pop("TIKTOKEN_RS_CACHE_DIR", None)
    result = subprocess.run([str(resolver)], env=env, capture_output=True,
                            text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()).name == "tiktoken-rs-cache"
    assert (tmp_path / "tiktoken-rs-cache").is_dir()
