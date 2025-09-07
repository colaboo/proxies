from pathlib import Path

def get_src_path() -> Path:
    """
    Get the path to the src directory, regardless of how the application is run.
    
    Returns:
        Path: Absolute path to the src directory
        
    Example:
        src_path = get_src_path()
        routes_path = src_path / "routes"
    """
    # Get the path of the current file (src/utils/__init__.py)
    # Then go up one level to reach src/
    return Path(__file__).resolve().parent.parent