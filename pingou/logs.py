import logging
from pathlib import Path
from rich.logging import RichHandler

from pingou.env import RELEASE_STAGE, BUGSNAG_ID

try:
    import bugsnag
    from bugsnag.handlers import BugsnagHandler
except ImportError:
    bugsnag = None

logger = logging.getLogger('pingou')


def init_bugsnag(app_version: str):
    if not bugsnag:
        raise ImportError('Bugsnag not installed')
    bugsnag.configure(
        api_key=BUGSNAG_ID,
        project_root=Path(__file__).parent / 'pingou',
        notify_release_stages=['production'],
        release_stage=RELEASE_STAGE,
        app_version=app_version
    )
    bugsnag_handler = BugsnagHandler()
    bugsnag_handler.setLevel(logging.ERROR)
    return bugsnag_handler


_LOG_FORMAT = "%(message)s"


def init_logging(
        log_lvl,
        logs_path: str = None,
        app_version: str = None):
    logging.basicConfig(
        level=log_lvl.upper() if isinstance(log_lvl, str) else log_lvl,
        format=_LOG_FORMAT,
        datefmt="[%X]",
        handlers=[
            RichHandler(show_path=False, rich_tracebacks=True)
        ]
    )

    if bugsnag is not None and app_version:
        bugsnag_handler = init_bugsnag(app_version)
        logger.addHandler(bugsnag_handler)
