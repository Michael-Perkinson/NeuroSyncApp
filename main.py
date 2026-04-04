import logging
from src.gui.views.tk_dashboard import TkDashboard

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler],
    format="%(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger(__name__)


def on_closing(app: TkDashboard) -> None:
    logger.info("Application is shutting down.")
    app.quit()
    app.destroy()


if __name__ == "__main__":
    try:
        app = TkDashboard()
        app.protocol("WM_DELETE_WINDOW", lambda: on_closing(app))
        app.run()
    except Exception as e:
        logger.error("Application failed to start: %s", e, exc_info=True)
