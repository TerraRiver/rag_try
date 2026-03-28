from pathlib import Path

from dotenv import load_dotenv


_ENV_LOADED = False


def load_project_env() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return

    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(dotenv_path=project_root / ".env")
    load_dotenv(dotenv_path=project_root / ".env.local", override=True)
    _ENV_LOADED = True
