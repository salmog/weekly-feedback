from datetime import datetime

import structlog
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from weekly.config import Settings
from weekly.ingestion.engine import IngestionEngine

logger = structlog.get_logger(__name__)


class SchedulerManager:
    def __init__(self, engine: IngestionEngine, settings: Settings) -> None:
        self._engine = engine
        self._settings = settings
        self._scheduler = BackgroundScheduler(timezone=settings.schedule_timezone)

    def start(self) -> None:
        self._scheduler.add_job(
            self._run_update,
            CronTrigger(
                hour=self._settings.schedule_after_close_hour,
                minute=self._settings.schedule_after_close_minute,
                day_of_week="mon-fri",
                timezone=self._settings.schedule_timezone,
            ),
            id="post_close_update",
            name="Post-Close Update",
            replace_existing=True,
            kwargs={"job_name": "post_close_update"},
        )

        self._scheduler.add_job(
            self._run_update,
            CronTrigger(
                hour=self._settings.schedule_before_open_hour,
                minute=self._settings.schedule_before_open_minute,
                day_of_week="mon-fri",
                timezone=self._settings.schedule_timezone,
            ),
            id="pre_open_update",
            name="Pre-Open Update",
            replace_existing=True,
            kwargs={"job_name": "pre_open_update"},
        )

        self._scheduler.start()
        logger.info("scheduler_started", jobs=len(self._scheduler.get_jobs()))

    def shutdown(self) -> None:
        self._scheduler.shutdown(wait=True)
        logger.info("scheduler_stopped")

    def _run_update(self, job_name: str = "scheduled_update") -> None:
        logger.info("scheduled_job_triggered", job=job_name)
        self._engine.run_full_update(trigger_type="scheduled")

    def get_next_run_times(self) -> dict[str, datetime | None]:
        result: dict[str, datetime | None] = {}
        for job in self._scheduler.get_jobs():
            next_run = job.next_run_time
            result[job.id] = next_run
        return result

    def get_jobs_info(self) -> list[dict]:
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
            }
            for job in self._scheduler.get_jobs()
        ]
