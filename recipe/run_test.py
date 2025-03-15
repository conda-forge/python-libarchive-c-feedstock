import sys
from subprocess import call
from pathlib import Path
import os
import pytest
import site
import shutil
from collections.abc import Iterator

WIN = sys.platform = "win32"
OSX = sys.platform = "darwin"
LINUX = sys.platform = "linux"
UNIX = not WIN
SP_DIR = Path(site.getsitepackages()[0])

HERE = Path(__file__).parent
FIXTURES = HERE / "tests"
ALL_FIXTURES = sorted(FIXTURES.glob("*"))

PYTEST = ["pytest", "-vv", "--color=yes", "--tb=long", __file__]
SKIPS = []
PYTEST_K = []
FAIL_UNDER = 0

if UNIX:
    PYTEST += ["tests"]
    SKIPS += [
        "unicode_entries",
    ]

if OSX:
    SKIPS = [
        "test_fd",
        "test_files",
        "test_buffers",
        "atime_ctime",
        "custom_writer",
    ]

if LINUX:
    FAIL_UNDER = 83

COV = ["coverage"]
RUN = ["run", "--source=libarchive", "--branch", "-m"]
REPORT = ["report", "--show-missing", "--skip-covered", f"--fail-under={FAIL_UNDER}"]

SKIP_OR = " or ".join(SKIPS)

if SKIPS:
    PYTEST_K = ["-k", f"not ({SKIP_OR})" if len(SKIPS) > 1 else SKIPS[0]]


@pytest.fixture
def in_tmp_path(tmp_path: Path) -> Iterator[Path]:
    old_cwd = os.getcwd()
    os.chdir(str(tmp_path))
    yield tmp_path
    os.chdir(old_cwd)


@pytest.mark.parametrize("path", [p.name for p in ALL_FIXTURES])
def test_extract_fixture(path: str, in_tmp_path: Path) -> None:
    import libarchive

    libarchive.extract_file(FIXTURES / path)
    assert (in_tmp_path / "hello_world").exists()


if __name__ == "__main__":
    if UNIX:
        print("... copying libarchive from site-packages to local for relative paths")
        shutil.copytree(SP_DIR / "libarchive", HERE / "libarchive")

    sys.exit(
        # run the tests
        call([*COV, *RUN, *PYTEST, *PYTEST_K])
        # maybe run coverage
        or (call([*COV, *REPORT]))
    )
