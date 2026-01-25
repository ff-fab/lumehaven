"""lumehaven - Smart home dashboard backend."""

try:
    # Try to get version from generated version file (updated by setuptools_scm at build time)
    from lumehaven._version import __version__
except ImportError:
    try:
        # Fallback to installed package metadata
        from importlib.metadata import version

        __version__ = version("lumehaven")
    except Exception:
        # Last resort fallback
        __version__ = "0.0.0+unknown"
