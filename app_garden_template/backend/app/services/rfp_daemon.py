"""
RFP Discovery Daemon Service - FIXED VERSION
Handles scheduled and on-demand RFP discovery with proper connection management
"""

import asyncio
import sqlite3
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
import logging

from croniter import croniter

from app.models.rfp import (
    RFPSearchRequest,
    RFPDiscoveryRun,
    RFPSchedule,
    DaemonStatus,
    RunStatus
)
from app.services.rfp_discovery_service import RFPDiscoveryService
from app.services.kamiwaza_service import KamiwazaService

logger = logging.getLogger(__name__)


class RFPDaemon:
    """Background daemon for scheduled RFP discovery"""

    def __init__(self, db_path: str = "data/rfp_daemon/rfp_daemon.db"):
        self.db_path = db_path
        self.is_running = False
        self.start_time = None
        self.current_run: Optional[RFPDiscoveryRun] = None
        self.recent_runs: List[RFPDiscoveryRun] = []
        self.schedules: Dict[str, RFPSchedule] = {}

        # Async management
        self.scheduler_task = None
        self.monitor_task = None
        self.shutdown_event = asyncio.Event()

        # FIX: Add locks to prevent race conditions
        self.schedule_locks: Dict[str, asyncio.Lock] = {}
        self.run_lock = asyncio.Lock()  # Prevent multiple concurrent runs

        # Services
        self.kamiwaza_service = KamiwazaService()
        self.discovery_service = RFPDiscoveryService(self.kamiwaza_service)

        # Initialize database
        self._init_database()

    @contextmanager
    def get_db_connection(self):
        """Context manager for database connections to prevent leaks"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def _init_database(self):
        """Initialize SQLite database for persistent state"""
        with self.get_db_connection() as conn:
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
                    run_mode TEXT DEFAULT 'normal',
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

        # FIX: Cancel any existing tasks before creating new ones
        await self._cleanup_tasks()

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

        # Clean up tasks
        await self._cleanup_tasks()

        logger.info("RFP Daemon stopped")

    async def _cleanup_tasks(self):
        """Clean up background tasks properly"""
        tasks_to_cancel = []

        if self.scheduler_task:
            tasks_to_cancel.append(self.scheduler_task)
            self.scheduler_task = None

        if self.monitor_task:
            tasks_to_cancel.append(self.monitor_task)
            self.monitor_task = None

        for task in tasks_to_cancel:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _scheduler_loop(self):
        """Main scheduler loop that checks and executes schedules"""
        logger.info("Scheduler loop started")

        while not self.shutdown_event.is_set():
            try:
                now = datetime.now()

                for schedule_id, schedule in self.schedules.items():
                    if not schedule.enabled:
                        continue

                    # FIX: Create lock for each schedule if not exists
                    if schedule_id not in self.schedule_locks:
                        self.schedule_locks[schedule_id] = asyncio.Lock()

                    # FIX: Use lock to prevent race condition
                    if self.schedule_locks[schedule_id].locked():
                        logger.debug(f"Schedule {schedule_id} is already running, skipping")
                        continue

                    async with self.schedule_locks[schedule_id]:
                        if self._should_run_schedule(schedule, now):
                            logger.info(f"Triggering scheduled run: {schedule.name}")
                            # Don't await here - let it run in background
                            asyncio.create_task(
                                self._run_discovery_with_lock(schedule.search_config, schedule_id)
                            )
                            # Update last_run time immediately to prevent re-triggering
                            self._update_schedule_last_run(schedule_id, now)

                await asyncio.sleep(5)  # Check every 5 seconds

            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(5)

    async def _run_discovery_with_lock(self, search_config: RFPSearchRequest, schedule_id: Optional[str] = None):
        """Wrapper to run discovery with proper locking"""
        try:
            await self._run_discovery(search_config, schedule_id)
        except Exception as e:
            logger.error(f"Discovery run failed: {e}")

    def _should_run_schedule(self, schedule: RFPSchedule, now: datetime) -> bool:
        """Check if a schedule should run now"""
        try:
            cron = croniter(schedule.cron_expression, now)

            # Get the last scheduled time
            prev_time = cron.get_prev(datetime)

            # Check if we haven't run since the last scheduled time
            if schedule.last_run:
                # Handle both string and datetime objects
                if isinstance(schedule.last_run, str):
                    last_run = datetime.fromisoformat(schedule.last_run)
                else:
                    last_run = schedule.last_run
                if last_run >= prev_time:
                    return False

            # Check if we're within 60 seconds of the scheduled time
            time_diff = (now - prev_time).total_seconds()
            return time_diff < 60

        except Exception as e:
            logger.error(f"Error checking schedule {schedule.schedule_id}: {e}")
            return False

    def _update_schedule_last_run(self, schedule_id: str, run_time: datetime):
        """Update schedule's last run time"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE rfp_schedules
                SET last_run = ?
                WHERE schedule_id = ?
            """, (run_time.isoformat(), schedule_id))
            conn.commit()

        if schedule_id in self.schedules:
            self.schedules[schedule_id].last_run = run_time.isoformat()

    async def _monitor_loop(self):
        """Monitor loop for cleanup and maintenance"""
        logger.info("Monitor loop started")

        while not self.shutdown_event.is_set():
            try:
                # Clean up old logs and runs
                self._cleanup_old_data()

                # Update next run times for schedules
                self._update_next_run_times()

                await asyncio.sleep(3600)  # Run every hour

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(3600)

    def _cleanup_old_data(self):
        """Clean up old runs and logs"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()

                # Delete logs older than 7 days
                seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
                cursor.execute("""
                    DELETE FROM rfp_logs
                    WHERE timestamp < ?
                """, (seven_days_ago,))

                # Delete runs older than 30 days
                thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
                cursor.execute("""
                    DELETE FROM rfp_runs
                    WHERE started_at < ?
                """, (thirty_days_ago,))

                conn.commit()

        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")

    def _update_next_run_times(self):
        """Update next run times for all schedules"""
        now = datetime.now()

        for schedule_id, schedule in self.schedules.items():
            if schedule.enabled:
                try:
                    cron = croniter(schedule.cron_expression, now)
                    next_time = cron.get_next(datetime)
                    schedule.next_run = next_time.isoformat()

                    with self.get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE rfp_schedules
                            SET next_run = ?
                            WHERE schedule_id = ?
                        """, (next_time.isoformat(), schedule_id))
                        conn.commit()

                except Exception as e:
                    logger.error(f"Error updating next run time for {schedule_id}: {e}")

    async def _run_discovery(self, search_config: RFPSearchRequest, schedule_id: Optional[str] = None):
        """Execute an RFP discovery run"""
        # FIX: Use run lock to prevent concurrent discovery runs
        async with self.run_lock:
            if self.current_run:
                raise Exception("A discovery run is already in progress")

            run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if schedule_id:
                run_id += f"_{schedule_id}"

            # Initialize run
            self.current_run = RFPDiscoveryRun(
                run_id=run_id,
                started_at=datetime.now(),
                status=RunStatus.RUNNING,
                search_config=search_config
            )

            # Log to database
            self._log_run_start(run_id, search_config)
            self._log_to_db(run_id, "INFO", "Discovery run started")

            try:
                # Execute discovery
                result = await self.discovery_service.discover_rfps(search_config)

                # Update current run with results
                self.current_run = result
                self.current_run.status = RunStatus.COMPLETED
                self.current_run.completed_at = datetime.now()

                # Log completion
                self._log_run_complete(run_id, result)
                self._log_to_db(run_id, "INFO", f"Discovery completed: {result.total_qualified} qualified RFPs")

                # Add to recent runs
                self.recent_runs.insert(0, result)
                if len(self.recent_runs) > 10:
                    self.recent_runs = self.recent_runs[:10]

            except Exception as e:
                logger.error(f"Discovery run failed: {e}")

                if self.current_run:
                    self.current_run.status = RunStatus.FAILED
                    self.current_run.completed_at = datetime.now()
                    self.current_run.errors.append({"error": str(e)})

                self._log_run_error(run_id, str(e))
                self._log_to_db(run_id, "ERROR", f"Discovery failed: {e}")
                raise

            finally:
                self.current_run = None

    def _load_schedules(self):
        """Load schedules from database"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM rfp_schedules WHERE enabled = 1")
                rows = cursor.fetchall()

                self.schedules = {}
                for row in rows:
                    schedule = RFPSchedule(
                        schedule_id=row["schedule_id"],
                        name=row["name"],
                        cron_expression=row["cron_expression"],
                        enabled=bool(row["enabled"]),
                        search_config=RFPSearchRequest(**json.loads(row["search_config"])),
                        last_run=row["last_run"],
                        next_run=row["next_run"]
                    )
                    self.schedules[schedule.schedule_id] = schedule
                    # Create lock for schedule
                    self.schedule_locks[schedule.schedule_id] = asyncio.Lock()

                logger.info(f"Loaded {len(self.schedules)} schedules from database")

        except Exception as e:
            logger.error(f"Error loading schedules: {e}")
            self.schedules = {}

    def add_schedule(self, schedule: RFPSchedule) -> str:
        """Add a new schedule"""
        try:
            # Generate ID if not provided
            if not schedule.schedule_id:
                schedule.schedule_id = f"schedule_{uuid.uuid4().hex[:8]}"

            # Save to database
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO rfp_schedules
                    (schedule_id, name, run_mode, cron_expression, enabled, search_config, last_run, next_run)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    schedule.schedule_id,
                    schedule.name,
                    schedule.run_mode if hasattr(schedule, 'run_mode') else 'normal',
                    schedule.cron_expression,
                    int(schedule.enabled),
                    json.dumps(schedule.search_config.dict()),
                    schedule.last_run,
                    schedule.next_run
                ))
                conn.commit()

            # Add to memory
            self.schedules[schedule.schedule_id] = schedule
            self.schedule_locks[schedule.schedule_id] = asyncio.Lock()

            # Calculate next run time
            self._update_next_run_times()

            logger.info(f"Added schedule: {schedule.name} ({schedule.schedule_id})")
            return schedule.schedule_id

        except Exception as e:
            logger.error(f"Error adding schedule: {e}")
            raise

    def update_schedule(self, schedule_id: str, updates: Dict[str, Any]):
        """Update an existing schedule"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()

                # Build update query
                update_fields = []
                values = []

                for field, value in updates.items():
                    if field in ["name", "cron_expression", "enabled", "search_config"]:
                        update_fields.append(f"{field} = ?")
                        if field == "search_config":
                            values.append(json.dumps(value) if isinstance(value, dict) else value)
                        else:
                            values.append(value)

                if update_fields:
                    values.append(schedule_id)
                    query = f"UPDATE rfp_schedules SET {', '.join(update_fields)} WHERE schedule_id = ?"
                    cursor.execute(query, values)
                    conn.commit()

                    # Reload schedule
                    if schedule_id in self.schedules:
                        self._load_schedules()

                    logger.info(f"Updated schedule: {schedule_id}")

        except Exception as e:
            logger.error(f"Error updating schedule: {e}")
            raise

    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule"""
        try:
            # Check if schedule exists
            if schedule_id not in self.schedules:
                return False

            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM rfp_schedules WHERE schedule_id = ?", (schedule_id,))
                conn.commit()

            # Remove from memory
            if schedule_id in self.schedules:
                del self.schedules[schedule_id]
            if schedule_id in self.schedule_locks:
                del self.schedule_locks[schedule_id]

            logger.info(f"Deleted schedule: {schedule_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting schedule: {e}")
            raise

    def trigger_immediate_run(self, search_config: RFPSearchRequest) -> str:
        """Trigger an immediate discovery run"""
        if not self.is_running:
            raise Exception("Daemon is not running")

        # Create a task for the discovery
        asyncio.create_task(self._run_discovery(search_config))

        return "Discovery run triggered successfully"

    def get_status(self) -> DaemonStatus:
        """Get current daemon status"""
        uptime = time.time() - self.start_time if self.start_time else 0

        return DaemonStatus(
            is_running=self.is_running,
            uptime_seconds=uptime,
            current_run=self.current_run,
            recent_runs=self.recent_runs[:10],
            active_schedules=list(self.schedules.values()),
            system_metrics={
                "memory_mb": self._get_memory_usage(),
                "schedule_count": len(self.schedules),
                "total_runs": len(self.recent_runs)
            }
        )

    def get_run_logs(self, run_id: str) -> List[Dict[str, Any]]:
        """Get logs for a specific run"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT timestamp, level, message, details
                    FROM rfp_logs
                    WHERE run_id = ?
                    ORDER BY timestamp
                """, (run_id,))

                logs = []
                for row in cursor.fetchall():
                    log_entry = {
                        "timestamp": row["timestamp"],
                        "level": row["level"],
                        "message": row["message"]
                    }
                    if row["details"]:
                        log_entry["details"] = json.loads(row["details"])
                    logs.append(log_entry)

                return logs

        except Exception as e:
            logger.error(f"Error getting run logs: {e}")
            return []

    def _log_run_start(self, run_id: str, search_config: RFPSearchRequest):
        """Log run start to database"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO rfp_runs
                    (run_id, started_at, status, search_config)
                    VALUES (?, ?, ?, ?)
                """, (
                    run_id,
                    datetime.now().isoformat(),
                    RunStatus.RUNNING.value,
                    json.dumps(search_config.dict())
                ))
                conn.commit()

        except Exception as e:
            logger.error(f"Error logging run start: {e}")

    def _log_run_complete(self, run_id: str, result: RFPDiscoveryRun):
        """Log run completion to database"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE rfp_runs SET
                        completed_at = ?,
                        status = ?,
                        total_found = ?,
                        total_processed = ?,
                        total_qualified = ?,
                        total_maybe = ?,
                        total_rejected = ?,
                        total_errors = ?,
                        processing_time_seconds = ?
                    WHERE run_id = ?
                """, (
                    datetime.now().isoformat(),
                    RunStatus.COMPLETED.value,
                    result.total_found,
                    result.total_processed,
                    result.total_qualified,
                    result.total_maybe,
                    result.total_rejected,
                    result.total_errors,
                    result.processing_time_seconds,
                    run_id
                ))
                conn.commit()

        except Exception as e:
            logger.error(f"Error logging run completion: {e}")

    def _log_run_error(self, run_id: str, error: str):
        """Log run error to database"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE rfp_runs SET
                        completed_at = ?,
                        status = ?,
                        errors = ?
                    WHERE run_id = ?
                """, (
                    datetime.now().isoformat(),
                    RunStatus.FAILED.value,
                    json.dumps([{"error": error}]),
                    run_id
                ))
                conn.commit()

        except Exception as e:
            logger.error(f"Error logging run error: {e}")

    def _log_to_db(self, run_id: str, level: str, message: str, details: Optional[Dict] = None):
        """Log message to database"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO rfp_logs
                    (run_id, timestamp, level, message, details)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    run_id,
                    datetime.now().isoformat(),
                    level,
                    message,
                    json.dumps(details) if details else None
                ))
                conn.commit()

        except Exception as e:
            logger.error(f"Error logging to database: {e}")

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0


# Singleton instance
_daemon_instance: Optional[RFPDaemon] = None

def get_daemon() -> RFPDaemon:
    """Get or create daemon instance"""
    global _daemon_instance
    if _daemon_instance is None:
        _daemon_instance = RFPDaemon()
    return _daemon_instance