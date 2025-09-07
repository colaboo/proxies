import importlib.util
import sys
import logging
from pathlib import Path
from typing import List, Optional, Sequence

from fastapi import APIRouter
from .get_src_path import get_src_path


logger = logging.getLogger(__name__)


def _is_ignored_path(path: Path) -> bool:
    """Return True if the path should be ignored during discovery."""
    parts = set(path.parts)
    return (
        "__pycache__" in parts
        or ".venv" in parts
        or ".env" in parts
        or ".git" in parts
    )


def _generate_module_name(routes_root: Path, file_path: Path) -> str:
    """Generate a unique, import-safe module name based on file path."""
    rel = file_path.relative_to(routes_root)
    # Replace characters that are invalid for module names
    safe = (
        str(rel)
        .replace("/", "__")
        .replace("\\", "__")
        .replace("-", "_")
        .replace(".", "_")
        .replace("[", "_")
        .replace("]", "_")
        .replace(" ", "_")
    )
    return f"dynamic_routes__{safe}"


def _iter_router_files(routes_root: Path):
    """Yield handlers.py files under routes/http and routes/ws (recursive within these only)."""
    for subdir in ("http", "ws"):
        base = routes_root / subdir
        if not base.exists() or not base.is_dir():
            continue
        for file_path in base.rglob("handlers.py"):
            if not file_path.is_file():
                continue
            if _is_ignored_path(file_path):
                continue
            yield file_path


def _load_module_from_path(module_name: str, file_path: Path):
    """Safely import a module from a file path. Returns module or None on error."""
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        logger.warning("Cannot create import spec for %s", file_path)
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module
    # try:
    #     spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    #     if spec is None or spec.loader is None:
    #         logger.warning("Cannot create import spec for %s", file_path)
    #         return None
    #     module = importlib.util.module_from_spec(spec)
    #     spec.loader.exec_module(module)  # type: ignore[attr-defined]
    #     return module
    # except Exception as exc:
    #     logger.error("Failed to import router module %s: %s", file_path, exc)
    #     return None


def load_routers(paths: Optional[Sequence[str]] = None, load_all: bool = False) -> List[APIRouter]:
    """
    Discover and import FastAPI APIRouter instances.

    Modes:
    - If 'paths' is provided: only search within these subpaths under routes/.
      Each path can be a directory (searched recursively) or a direct file path
      to a handlers.py file.
    - Else if load_all is True: search under routes/http/** and routes/ws/**.
    - Else: return an empty list.

    - Only looks for files named "handlers.py".
    - Collects variables named "router" that are APIRouter instances.
    - Skips modules that fail to import without stopping discovery.

    Usage in main.py:
        from utils import load_routers
        for router in load_routers(load_all=True):
            app.include_router(router)
    """
    # Ensure absolute imports work when dynamically importing files by path.
    # Add both project root and src/ to sys.path.
    src_path = get_src_path()
    project_root = src_path.parent
    project_root_str = str(project_root)
    src_path_str = str(src_path)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    if src_path_str not in sys.path:
        sys.path.insert(0, src_path_str)
    routes_root = src_path / "routes"
    if not routes_root.exists():
        logger.warning("Routes directory not found: %s", routes_root)
        return []

    # Determine candidate files to load
    candidate_files: List[Path] = []
    if paths:
        for sub in paths:
            base = (routes_root / sub).resolve()
            # Ensure the path stays under routes_root
            try:
                base.relative_to(routes_root)
            except ValueError:
                logger.warning("Skipping path outside routes root: %s", base)
                continue
            if base.is_dir():
                candidate_files.extend([p for p in base.rglob("handlers.py") if p.is_file() and not _is_ignored_path(p)])
            elif base.is_file():
                if base.name == "handlers.py" and not _is_ignored_path(base):
                    candidate_files.append(base)
            else:
                logger.debug("Path not found: %s", base)
    elif load_all:
        candidate_files.extend(list(_iter_router_files(routes_root)))
    else:
        return []
    routers: List[APIRouter] = []
    for file_path in candidate_files:
        module_name = _generate_module_name(routes_root, file_path)
        module = _load_module_from_path(module_name, file_path)
        if module is None:
            continue

        router_obj = getattr(module, "router", None)
        if isinstance(router_obj, APIRouter):
            routers.append(router_obj)
        else:
            # Not an APIRouter-based handler; ignore silently
            logger.debug("No APIRouter 'router' in %s", file_path)

    return routers

