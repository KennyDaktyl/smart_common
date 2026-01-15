# smart_common/smart_logging/custom_rotating_handler.py
import logging
import os
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler


class AdvancedRotatingFileHandler(TimedRotatingFileHandler):

    def __init__(self, base_log_dir, filename="app.log", retention_days=365):
        self.base_log_dir = base_log_dir
        self.retention_days = retention_days

        os.makedirs(self.base_log_dir, exist_ok=True)

        log_path = os.path.join(self.base_log_dir, filename)

        super().__init__(
            log_path,
            when="midnight",
            interval=1,
            backupCount=0,
            encoding="utf-8",
            utc=False,
        )

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None

        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")

        target_dir = os.path.join(self.base_log_dir, year, month)
        os.makedirs(target_dir, exist_ok=True)

        dest_file = os.path.join(target_dir, f"{now.strftime('%Y-%m-%d')}.log")

        if os.path.exists(self.baseFilename):
            os.rename(self.baseFilename, dest_file)

        self.stream = self._open()
        self._cleanup_old_logs()

    def _cleanup_old_logs(self):
        """Prune log files older than the configured retention period."""
        if self.retention_days <= 0:
            return

        cutoff = datetime.now() - timedelta(days=self.retention_days)
        for root, _, files in os.walk(self.base_log_dir):
            for filename in files:
                file_path = os.path.join(root, filename)
                if file_path == self.baseFilename:
                    continue

                try:
                    modification_time = datetime.fromtimestamp(
                        os.path.getmtime(file_path)
                    )
                except OSError:
                    continue

                if modification_time >= cutoff:
                    continue

                try:
                    os.remove(file_path)
                except OSError:
                    continue
