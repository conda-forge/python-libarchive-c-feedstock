import sys
from subprocess import call
from pathlib import Path
import urllib.request
import os
from io import BytesIO
import pytest
import site
import tarfile
import shutil
import platform
from typing import Any
from collections.abc import Iterator

UTF8 = {"encoding": "utf-8"}
PKG_VERSION = os.environ["PKG_VERSION"]
SDIST_URL = (
    f"https://pypi.org/packages/source/l/libarchive-c/libarchive_c-{PKG_VERSION}.tar.gz"
)

PLAT = platform.system()
WIN = PLAT == "Windows"
OSX = PLAT == "Darwin"
LINUX = PLAT == "Linux"

if not (LINUX or OSX or WIN):
    raise RuntimeError(f"Unknown platform: {PLAT}")

SP_DIR = Path(site.getsitepackages()[0])
TESTS_IN_SP_DIR = SP_DIR / "tests"

HERE = Path(__file__).parent
FIXTURES = HERE / "test"
ALL_FIXTURES = sorted(FIXTURES.glob("*"))
SDIST_EXTRACTED = HERE / f"src/libarchive_c-{PKG_VERSION}"

PYTEST = ["pytest", "-vv", "--color=yes", "--tb=long", __file__]
SKIPS = []
PYTEST_K = []

USE_SDIST_TESTS = True

if OSX:
    FAIL_UNDER = 76
    SKIPS += [
        "test_fd",
        "test_files",
        "test_buffers",
        "atime_ctime",
        "custom_writer",
    ]
elif LINUX:
    FAIL_UNDER = 79
elif WIN:
    # too many fails based on POSIX assumptions to be relevant
    USE_SDIST_TESTS = False
    FAIL_UNDER = 49

if USE_SDIST_TESTS:
    PYTEST += [str(TESTS_IN_SP_DIR)]

COV = ["coverage"]
RUN = ["run", "--source=libarchive", "--branch", "-m"]
REPORT = ["report", "--show-missing", "--skip-covered", f"--fail-under={FAIL_UNDER}"]

SKIP_OR = " or ".join(SKIPS)

if SKIPS:
    PYTEST_K = ["-k", f"not ({SKIP_OR})" if len(SKIPS) > 1 else f"not {SKIPS[0]}"]


@pytest.fixture
def in_tmp_path(tmp_path: Path) -> Iterator[Path]:
    old_cwd = os.getcwd()
    os.chdir(str(tmp_path))
    yield tmp_path
    os.chdir(old_cwd)


@pytest.mark.parametrize("path", [p.name for p in ALL_FIXTURES])
def test_conda_forge_extract_fixture(path: str, in_tmp_path: Path) -> None:
    import libarchive

    libarchive.extract_file(str(FIXTURES / path))
    assert (in_tmp_path / "hello_world").exists()


def preflight() -> int:
    if USE_SDIST_TESTS:
        print("... fetching", SDIST_URL, flush=True)
        with urllib.request.urlopen(SDIST_URL) as req:
            io = BytesIO(req.read())
        io.seek(0)
        with tarfile.open(fileobj=io, mode="r:gz") as tf:
            tf.extractall(HERE / "src")

        test_entry = SDIST_EXTRACTED / "tests/test_entry.py"
        print("... patching f-strings in", test_entry)
        test_entry.write_text(
            test_entry.read_text(**UTF8).replace("'21'", '"21"'),
            **UTF8
        )

        print("... copying into", SP_DIR)
        shutil.copytree(SDIST_EXTRACTED / "tests", TESTS_IN_SP_DIR)
        shutil.copy2(SDIST_EXTRACTED / "README.rst", SP_DIR / "README.rst")
    return 0


if __name__ == "__main__":

    def do(args: list[str], **kwargs: Any) -> int:
        print(">>>", " \\\n\t".join(args), flush=True)
        return call(args, **kwargs)

    sys.exit(
        # maybe fetch the sdist, which contains file names windows can't handle
        preflight()
        # run the tests
        or do([*COV, *RUN, *PYTEST, *PYTEST_K], cwd=str(SP_DIR))
        # maybe run coverage
        or (do([*COV, *REPORT], cwd=str(SP_DIR)))
    )
