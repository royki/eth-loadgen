# eth-loadgen package
"""Version is read from pyproject.toml"""
from pathlib import Path
import re

try:
    from importlib.metadata import version, PackageNotFoundError  # Python 3.8+
except ImportError:
    # Python < 3.8 fallback (shouldn't happen with Python 3.10+)
    try:
        from importlib_metadata import version, PackageNotFoundError  # type: ignore
    except ImportError:
        version = None  # type: ignore
        PackageNotFoundError = Exception  # type: ignore

try:
    if version:
        __version__ = version("eth-loadgen")
    else:
        raise PackageNotFoundError()
except (PackageNotFoundError, AttributeError):
    # Package not installed (e.g., running from source)
    # Fallback: read from pyproject.toml using regex (no TOML parser needed)
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    if pyproject_path.exists():
        content = pyproject_path.read_text()
        match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
        __version__ = match.group(1) if match else "0.0.0"
    else:
        __version__ = "0.0.0"
