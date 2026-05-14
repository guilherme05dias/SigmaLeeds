import threading
from dataclasses import dataclass


@dataclass
class ProgressState:
    total: int = 0
    processed: int = 0
    pending: int = 0
    sent: int = 0
    failed: int = 0
    invalid: int = 0
    status: str = "Aguardando"


class CampaignRunner:
    def __init__(self):
        self._lock = threading.RLock()
        self.stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        self.campaign_id: int | None = None
        self.params: dict | None = None
        self.attachment: str | None = None
        self.excel_path: str | None = None
        self.was_stopped: bool = False
        self.progress = ProgressState()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def stop_requested(self) -> bool:
        return self.stop_event.is_set()

    def start(self, campaign_id: int, params: dict,
              target_fn, daemon: bool = True) -> bool:
        with self._lock:
            if self.is_running:
                return False
            self.stop_event.clear()
            self.was_stopped = False
            self.campaign_id = campaign_id
            self.params = params.copy()
            self._thread = threading.Thread(
                target=target_fn,
                daemon=daemon
            )
            self._thread.start()
            return True

    def stop(self):
        self.stop_event.set()

    def reset_progress(self, total: int = 0, pending: int = 0):
        with self._lock:
            self.progress = ProgressState(
                total=total,
                processed=0,
                pending=pending,
                sent=0,
                failed=0,
                invalid=0,
                status="Iniciando"
            )

    def update_progress(self, **kwargs):
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self.progress, k):
                    setattr(self.progress, k, v)

    def set_excel(self, path, campaign_id):
        with self._lock:
            self.excel_path = path
            self.campaign_id = campaign_id

    def set_attachment(self, path):
        with self._lock:
            self.attachment = path

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "is_running": self.is_running,
                "stop_requested": self.stop_requested,
                "campaign_id": self.campaign_id,
                "was_stopped": self.was_stopped,
                "attachment": self.attachment,
                "excel_path": self.excel_path,
                **self.progress.__dict__,
            }
