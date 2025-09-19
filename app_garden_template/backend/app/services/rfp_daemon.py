"""
RFP Discovery Daemon Service
Continuously running service for scheduled RFP discovery
"""

import asyncio
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from croniter import croniter

from app.services.rfp_discovery_service import RFPDiscoveryService
from app.services.kamiwaza_service import KamiwazaService
from app.models.rfp import (
    RFPDiscoveryRun,
    RFPSchedule,
    DaemonStatus,
    RFPSearchRequest,
    RunStatus,
    RFPLogEntry,
    RFPRunLogs
)

logger = logging.getLogger(__name__)


class RFPDaemon:
    """Daemon service for continuous RFP discovery"""

    def __init__(self, data_dir: str = "data/rfp_daemon"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.data_dir / "rfp_daemon.db"
        self.is_running = False
        self.current_run: Optional[RFPDiscoveryRun] = None
        self.start_time = None
        self.schedules: Dict[str, RFPSchedule] = {}
        self.recent_runs: List[RFPDiscoveryRun] = []
        self.max_recent_runs = 10

        # Initialize database
        self._init_database()

        # Initialize services
        self.kamiwaza_service = KamiwazaService()
        self.discovery_service = RFPDiscoveryService(self.kamiwaza_service)

        # Event for graceful shutdown
        self.shutdown_event = asyncio.Event()

        # Background tasks
        self.scheduler_task = None
        self.monitor_task = None

    def _init_database(self):
        """Initialize SQLite database for persistent state"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rfp_runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT NOT NULL,
                total_found INTEGER DEFAULT 0,
                total_processed INTEGER DEFAULT 0,
                total_qualified INTEGER DEFAULT 0,
                total_maybe INTEGER DEFAULT 0,
                total_rejected INTEGER DEFAULT 0,
                total_errors INTEGER DEFAULT 0,
                processing_time_seconds REAL,
                search_config TEXT,
                errors TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rfp_schedules (
                schedule_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                cron_expression TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                search_config TEXT NOT NULL,
                last_run TEXT,
                next_run TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rfp_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT,
                FOREIGN KEY (run_id) REFERENCES rfp_runs (run_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_run_id ON rfp_logs (run_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON rfp_logs (timestamp)
        """)

        conn.commit()
        conn.close()

    async def start(self):
        """Start the daemon service"""
        if self.is_running:
            logger.warning("Daemon is already running")
            return

        logger.info("Starting RFP Daemon")
        self.is_running = True
        self.start_time = time.time()

        # Load schedules from database
        self._load_schedules()

        # Start background tasks
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        self.monitor_task = asyncio.create_task(self._monitor_loop())

        logger.info(f"RFP Daemon started with {len(self.schedules)} schedules")

    async def stop(self):
        """Stop the daemon service gracefully"""
        if not self.is_running:
            logger.warning("Daemon is not running")
            return

        logger.info("Stopping RFP Daemon")
        self.is_running = False

        # Signal shutdown
        self.shutdown_event.set()

        # Cancel background tasks
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass

        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("RFP Daemon stopped")

    async def _scheduler_loop(self):
        """Main scheduler loop that runs scheduled discoveries"""
        while self.is_running:
            try:
                # Check each schedule
                for schedule_id, schedule in self.schedules.items():
                    if not schedule.enabled:
                        continue

                    # Check if it's time to run
                    now = datetime.now()
                    if self._should_run_schedule(schedule, now):
                        logger.info(f"Triggering scheduled run: {schedule.name}")
                        asyncio.create_task(
                            self._run_discovery(schedule.search_config, schedule_id)
                        )

                        # Update last run time
                        schedule.last_run = now
                        schedule.next_run = self._calculate_next_run(schedule.cron_expression)
                        self._update_schedule_in_db(schedule)

                # Sleep for a minute before checking again
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)

    async def _monitor_loop(self):
        """Monitor system resources and cleanup old data"""
        while self.is_running:
            try:
                # Cleanup old logs (keep last 7 days)
                self._cleanup_old_logs(days=7)

                # Cleanup old runs (keep last 30 days)
                self._cleanup_old_runs(days=30)

                # Log system metrics
                metrics = self.get_system_metrics()
                logger.debug(f"System metrics: {metrics}")

                # Sleep for 5 minutes
                await asyncio.sleep(300)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(300)

    def _should_run_schedule(self, schedule: RFPSchedule, now: datetime) -> bool:
        """Check if a schedule should run now"""
        if not schedule.enabled:
            return False

        # If never run, run now
        if not schedule.last_run:
            return True

        # Check cron expression
        cron = croniter(schedule.cron_expression, schedule.last_run)
        next_run = cron.get_next(datetime)

        return now >= next_run

    def _calculate_next_run(self, cron_expression: str) -> datetime:
        """Calculate next run time based on cron expression"""
        cron = croniter(cron_expression, datetime.now())
        return cron.get_next(datetime)

    async def _run_discovery(self, search_config: RFPSearchRequest, schedule_id: Optional[str] = None):
        """Run a discovery job"""
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        if schedule_id:
            run_id = f"{run_id}_{schedule_id}"

        # Log start
        self._log_to_db(run_id, "INFO", f"Starting discovery run {run_id}")

        try:
            # Set current run
            self.current_run = RFPDiscoveryRun(
                run_id=run_id,
                started_at=datetime.now(),
                status=RunStatus.RUNNING,
                search_config=search_config
            )

            # Run discovery
            result = await self.discovery_service.discover_rfps(search_config)

            # Save to database
            self._save_run_to_db(result)

            # Add to recent runs
            self.recent_runs.insert(0, result)
            if len(self.recent_runs) > self.max_recent_runs:
                self.recent_runs.pop()

            # Log completion
            self._log_to_db(
                run_id,
                "INFO",
                f"Discovery completed: {result.total_qualified} qualified, "
                f"{result.total_maybe} maybe, {result.total_rejected} rejected"
            )

            # Update Google Sheets if configured
            await self._update_google_sheets(result)

        except Exception as e:
            logger.error(f"Discovery run {run_id} failed: {e}")
            self._log_to_db(run_id, "ERROR", f"Discovery failed: {str(e)}")

            if self.current_run and self.current_run.run_id == run_id:
                self.current_run.status = RunStatus.FAILED
                self.current_run.errors.append({
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })

        finally:
            # Clear current run
            if self.current_run and self.current_run.run_id == run_id:
                self.current_run = None

    async def _update_google_sheets(self, run: RFPDiscoveryRun):
        """Update Google Sheets with discovery results"""
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

            from src.sheets_manager import SheetsManager
            from config import Config

            sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)

            # Update main sheet with qualified RFPs
            if run.qualified_rfps and Config.SPREADSHEET_ID:
                for rfp in run.qualified_rfps:
                    sheets_manager.add_rfp_to_sheet(
                        spreadsheet_id=Config.SPREADSHEET_ID,
                        opportunity=rfp.opportunity.dict(),
                        assessment=rfp.assessment.dict(),
                        folder_url=rfp.drive_folder_url
                    )
                run.sheets_updated["main"] = True

            # Update maybe sheet
            if run.maybe_rfps and Config.MAYBE_SPREADSHEET_ID:
                for rfp in run.maybe_rfps:
                    sheets_manager.add_rfp_to_sheet(
                        spreadsheet_id=Config.MAYBE_SPREADSHEET_ID,
                        opportunity=rfp.opportunity.dict(),
                        assessment=rfp.assessment.dict(),
                        folder_url=rfp.drive_folder_url
                    )
                run.sheets_updated["maybe"] = True

            # Update spam sheet with all RFPs
            if Config.SPAM_SPREADSHEET_ID:
                all_rfps = run.qualified_rfps + run.maybe_rfps + run.rejected_rfps
                for rfp in all_rfps:
                    sheets_manager.add_rfp_to_sheet(
                        spreadsheet_id=Config.SPAM_SPREADSHEET_ID,
                        opportunity=rfp.opportunity.dict(),
                        assessment=rfp.assessment.dict(),
                        folder_url=rfp.drive_folder_url
                    )
                run.sheets_updated["spam"] = True

            logger.info(f"Updated Google Sheets: {run.sheets_updated}")

        except Exception as e:
            logger.error(f"Failed to update Google Sheets: {e}")

    def trigger_immediate_run(self, search_config: RFPSearchRequest) -> str:
        """Trigger an immediate discovery run"""
        if self.current_run:
            raise Exception("A discovery run is already in progress")

        # Create task for async execution
        asyncio.create_task(self._run_discovery(search_config))

        return f"Discovery run triggered at {datetime.now()}"

    def add_schedule(self, schedule: RFPSchedule) -> str:
        """Add a new schedule"""
        # Calculate next run
        schedule.next_run = self._calculate_next_run(schedule.cron_expression)

        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO rfp_schedules
            (schedule_id, name, cron_expression, enabled, search_config, next_run)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            schedule.schedule_id,
            schedule.name,
            schedule.cron_expression,
            schedule.enabled,
            json.dumps(schedule.search_config.dict()),
            schedule.next_run.isoformat() if schedule.next_run else None
        ))

        conn.commit()
        conn.close()

        # Add to memory
        self.schedules[schedule.schedule_id] = schedule

        logger.info(f"Added schedule: {schedule.name}")
        return schedule.schedule_id

    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a schedule"""
        if schedule_id not in self.schedules:
            return False

        # Remove from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rfp_schedules WHERE schedule_id = ?", (schedule_id,))
        conn.commit()
        conn.close()

        # Remove from memory
        del self.schedules[schedule_id]

        logger.info(f"Removed schedule: {schedule_id}")
        return True

    def get_status(self) -> DaemonStatus:
        """Get current daemon status"""
        uptime = time.time() - self.start_time if self.start_time else 0

        return DaemonStatus(
            is_running=self.is_running,
            uptime_seconds=uptime,
            current_run=self.current_run,
            recent_runs=self.recent_runs[:10],
            active_schedules=list(self.schedules.values()),
            system_metrics=self.get_system_metrics()
        )

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system resource metrics"""
        import psutil

        process = psutil.Process()

        return {
            "cpu_percent": process.cpu_percent(),
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "threads": process.num_threads(),
            "open_files": len(process.open_files()),
            "daemon_uptime_hours": (time.time() - self.start_time) / 3600 if self.start_time else 0
        }

    def get_run_logs(self, run_id: str, limit: int = 1000) -> RFPRunLogs:
        """Get logs for a specific run"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT timestamp, level, message, details
            FROM rfp_logs
            WHERE run_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (run_id, limit))

        entries = []
        for row in cursor.fetchall():
            entries.append(RFPLogEntry(
                timestamp=datetime.fromisoformat(row[0]),
                level=row[1],
                message=row[2],
                details=json.loads(row[3]) if row[3] else None
            ))

        conn.close()

        return RFPRunLogs(
            run_id=run_id,
            entries=entries,
            total_entries=len(entries)
        )

    def _load_schedules(self):
        """Load schedules from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT schedule_id, name, cron_expression, enabled, search_config, last_run, next_run
            FROM rfp_schedules
            WHERE enabled = 1
        """)

        for row in cursor.fetchall():
            schedule = RFPSchedule(
                schedule_id=row[0],
                name=row[1],
                cron_expression=row[2],
                enabled=bool(row[3]),
                search_config=RFPSearchRequest(**json.loads(row[4])),
                last_run=datetime.fromisoformat(row[5]) if row[5] else None,
                next_run=datetime.fromisoformat(row[6]) if row[6] else None
            )
            self.schedules[schedule.schedule_id] = schedule

        conn.close()
        logger.info(f"Loaded {len(self.schedules)} schedules from database")

    def _save_run_to_db(self, run: RFPDiscoveryRun):
        """Save run to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO rfp_runs
            (run_id, started_at, completed_at, status, total_found, total_processed,
             total_qualified, total_maybe, total_rejected, total_errors,
             processing_time_seconds, search_config, errors)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run.run_id,
            run.started_at.isoformat(),
            run.completed_at.isoformat() if run.completed_at else None,
            run.status.value,
            run.total_found,
            run.total_processed,
            run.total_qualified,
            run.total_maybe,
            run.total_rejected,
            run.total_errors,
            run.processing_time_seconds,
            json.dumps(run.search_config.dict()),
            json.dumps(run.errors) if run.errors else None
        ))

        conn.commit()
        conn.close()

    def _update_schedule_in_db(self, schedule: RFPSchedule):
        """Update schedule in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE rfp_schedules
            SET last_run = ?, next_run = ?
            WHERE schedule_id = ?
        """, (
            schedule.last_run.isoformat() if schedule.last_run else None,
            schedule.next_run.isoformat() if schedule.next_run else None,
            schedule.schedule_id
        ))

        conn.commit()
        conn.close()

    def _log_to_db(self, run_id: str, level: str, message: str, details: Optional[Dict] = None):
        """Log to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO rfp_logs (run_id, timestamp, level, message, details)
            VALUES (?, ?, ?, ?, ?)
        """, (
            run_id,
            datetime.now().isoformat(),
            level,
            message,
            json.dumps(details) if details else None
        ))

        conn.commit()
        conn.close()

    def _cleanup_old_logs(self, days: int):
        """Remove logs older than specified days"""
        cutoff = datetime.now() - timedelta(days=days)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM rfp_logs
            WHERE timestamp < ?
        """, (cutoff.isoformat(),))

        deleted = cursor.rowcount
        if deleted > 0:
            logger.debug(f"Cleaned up {deleted} old log entries")

        conn.commit()
        conn.close()

    def _cleanup_old_runs(self, days: int):
        """Remove runs older than specified days"""
        cutoff = datetime.now() - timedelta(days=days)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Delete old runs and their logs
        cursor.execute("""
            DELETE FROM rfp_runs
            WHERE started_at < ?
        """, (cutoff.isoformat(),))

        deleted = cursor.rowcount
        if deleted > 0:
            logger.debug(f"Cleaned up {deleted} old runs")

        conn.commit()
        conn.close()


# Global daemon instance
daemon_instance: Optional[RFPDaemon] = None


def get_daemon() -> RFPDaemon:
    """Get or create daemon instance"""
    global daemon_instance
    if not daemon_instance:
        daemon_instance = RFPDaemon()
    return daemon_instance