import logging
import os
from datetime import datetime, timedelta


class AdvancedRotatingFileHandler(logging.FileHandler):
    """
    Jeden aktywny plik logu + dzienna archiwizacja.
    Brak nadpisywania plików.
    """

    def __init__(self, base_log_dir, filename="service.log", retention_days=365):
        self.base_log_dir = base_log_dir
        self.retention_days = retention_days

        os.makedirs(base_log_dir, exist_ok=True)

        self.current_date = datetime.now().date()
        path = os.path.join(base_log_dir, filename)

        super().__init__(path, encoding="utf-8")

    def emit(self, record):
        today = datetime.now().date()
        if today != self.current_date:
            self._rotate(today)
        super().emit(record)

    def _rotate(self, today):
        self.close()

        year = self.current_date.strftime("%Y")
        month = self.current_date.strftime("%m")
        target_dir = os.path.join(self.base_log_dir, year, month)
        os.makedirs(target_dir, exist_ok=True)

        archive_path = os.path.join(
            target_dir,
            f"{self.current_date.isoformat()}.log",
        )

        if os.path.exists(self.baseFilename):
            os.rename(self.baseFilename, archive_path)

        self.current_date = today
        self.stream = self._open()

        self._cleanup_old_logs()

    def _cleanup_old_logs(self):
        if self.retention_days <= 0:
            return

        cutoff = datetime.now() - timedelta(days=self.retention_days)

        for root, _, files in os.walk(self.base_log_dir):
            for file in files:
                path = os.path.join(root, file)
                if path == self.baseFilename:
                    continue
                try:
                    if datetime.fromtimestamp(os.path.getmtime(path)) < cutoff:
                        os.remove(path)
                except OSError:
                    pass
