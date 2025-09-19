"""
RFP Discovery API Routes
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import StreamingResponse

from app.models.rfp import (
    RFPSearchRequest,
    RFPDiscoveryRun,
    RFPSchedule,
    DaemonStatus,
    RFPRunLogs,
    ProcessedRFP
)
from app.models.settings import Settings
from app.services.rfp_discovery_service import RFPDiscoveryService
from app.services.rfp_daemon import get_daemon, RFPDaemon
from app.services.kamiwaza_service import KamiwazaService
from app.services.settings_service import get_settings_service
from app.core.errors import ServiceError

logger = logging.getLogger(__name__)

# Create router with prefix
router = APIRouter(prefix="/api/rfp", tags=["RFP Discovery"])


def get_rfp_service() -> RFPDiscoveryService:
    """Dependency to get RFP discovery service"""
    kamiwaza_service = KamiwazaService()
    return RFPDiscoveryService(kamiwaza_service)


def get_rfp_daemon() -> RFPDaemon:
    """Dependency to get RFP daemon"""
    return get_daemon()


# ==================== Discovery Endpoints ====================


@router.post("/discover", response_model=RFPDiscoveryRun)
async def discover_rfps(
    request: RFPSearchRequest,
    background_tasks: BackgroundTasks,
    service: RFPDiscoveryService = Depends(get_rfp_service)
):
    """
    Run RFP discovery immediately

    This endpoint triggers an immediate RFP discovery run with the specified
    configuration. The discovery runs asynchronously and returns the run status.
    """
    try:
        logger.info(f"Starting RFP discovery with model {request.model_name}")

        # Run discovery
        result = await service.discover_rfps(request)

        logger.info(
            f"Discovery completed: {result.total_qualified} qualified, "
            f"{result.total_maybe} maybe, {result.total_rejected} rejected"
        )

        return result

    except ServiceError as e:
        logger.error(f"Discovery failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in discovery: {e}")
        raise HTTPException(status_code=500, detail="Discovery failed unexpectedly")


@router.post("/discover/background")
async def discover_rfps_background(
    request: RFPSearchRequest,
    daemon: RFPDaemon = Depends(get_rfp_daemon)
):
    """
    Trigger RFP discovery to run in background

    This starts a discovery run in the background and returns immediately.
    Use the /status endpoint to check progress.
    """
    try:
        result = daemon.trigger_immediate_run(request)
        return {
            "status": "triggered",
            "message": result,
            "check_status_at": "/api/rfp/daemon/status"
        }
    except Exception as e:
        logger.error(f"Failed to trigger background discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent", response_model=List[ProcessedRFP])
async def get_recent_rfps(
    qualification_level: Optional[str] = None,
    limit: int = 50,
    daemon: RFPDaemon = Depends(get_rfp_daemon)
):
    """
    Get recently discovered RFPs

    Returns the most recent RFPs from completed discovery runs.
    Can filter by qualification level: qualified, maybe, rejected
    """
    all_rfps = []

    # Collect RFPs from recent runs
    for run in daemon.recent_runs[:5]:  # Last 5 runs
        if qualification_level == "qualified":
            all_rfps.extend(run.qualified_rfps)
        elif qualification_level == "maybe":
            all_rfps.extend(run.maybe_rfps)
        elif qualification_level == "rejected":
            all_rfps.extend(run.rejected_rfps)
        else:
            # Return all
            all_rfps.extend(run.qualified_rfps)
            all_rfps.extend(run.maybe_rfps)
            all_rfps.extend(run.rejected_rfps)

    # Sort by score (highest first) and limit
    all_rfps.sort(key=lambda x: x.assessment.relevance_score, reverse=True)

    return all_rfps[:limit]


# ==================== Daemon Control Endpoints ====================


@router.post("/daemon/start")
async def start_daemon(daemon: RFPDaemon = Depends(get_rfp_daemon)):
    """Start the RFP discovery daemon"""
    try:
        await daemon.start()
        return {"status": "started", "message": "RFP daemon is now running"}
    except Exception as e:
        logger.error(f"Failed to start daemon: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/daemon/stop")
async def stop_daemon(daemon: RFPDaemon = Depends(get_rfp_daemon)):
    """Stop the RFP discovery daemon"""
    try:
        await daemon.stop()
        return {"status": "stopped", "message": "RFP daemon has been stopped"}
    except Exception as e:
        logger.error(f"Failed to stop daemon: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daemon/status", response_model=DaemonStatus)
async def get_daemon_status(daemon: RFPDaemon = Depends(get_rfp_daemon)):
    """Get current daemon status and metrics"""
    return daemon.get_status()


# ==================== Schedule Management ====================


@router.get("/schedules", response_model=List[RFPSchedule])
async def list_schedules(daemon: RFPDaemon = Depends(get_rfp_daemon)):
    """List all configured schedules"""
    return list(daemon.schedules.values())


@router.post("/schedules", response_model=str)
async def create_schedule(
    schedule: RFPSchedule,
    daemon: RFPDaemon = Depends(get_rfp_daemon)
):
    """Create a new discovery schedule"""
    try:
        schedule_id = daemon.add_schedule(schedule)
        return schedule_id
    except Exception as e:
        logger.error(f"Failed to create schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/schedules/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    schedule: RFPSchedule,
    daemon: RFPDaemon = Depends(get_rfp_daemon)
):
    """Update an existing schedule"""
    try:
        # Remove old schedule
        if not daemon.remove_schedule(schedule_id):
            raise HTTPException(status_code=404, detail="Schedule not found")

        # Add updated schedule
        schedule.schedule_id = schedule_id
        daemon.add_schedule(schedule)

        return {"status": "updated", "schedule_id": schedule_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    daemon: RFPDaemon = Depends(get_rfp_daemon)
):
    """Delete a schedule"""
    if not daemon.remove_schedule(schedule_id):
        raise HTTPException(status_code=404, detail="Schedule not found")

    return {"status": "deleted", "schedule_id": schedule_id}


# ==================== Run History & Logs ====================


@router.get("/runs", response_model=List[RFPDiscoveryRun])
async def list_runs(
    limit: int = 10,
    daemon: RFPDaemon = Depends(get_rfp_daemon)
):
    """List recent discovery runs"""
    return daemon.recent_runs[:limit]


@router.get("/runs/{run_id}", response_model=RFPDiscoveryRun)
async def get_run_details(
    run_id: str,
    daemon: RFPDaemon = Depends(get_rfp_daemon)
):
    """Get details of a specific run"""
    # Check current run
    if daemon.current_run and daemon.current_run.run_id == run_id:
        return daemon.current_run

    # Check recent runs
    for run in daemon.recent_runs:
        if run.run_id == run_id:
            return run

    raise HTTPException(status_code=404, detail="Run not found")


@router.get("/runs/{run_id}/logs", response_model=RFPRunLogs)
async def get_run_logs(
    run_id: str,
    limit: int = 1000,
    daemon: RFPDaemon = Depends(get_rfp_daemon)
):
    """Get logs for a specific discovery run"""
    try:
        logs = daemon.get_run_logs(run_id, limit)
        if not logs.entries:
            raise HTTPException(status_code=404, detail="No logs found for this run")
        return logs
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs/{run_id}/logs/stream")
async def stream_run_logs(
    run_id: str,
    daemon: RFPDaemon = Depends(get_rfp_daemon)
):
    """Stream logs for a run in real-time (SSE)"""

    async def generate():
        last_check = datetime.now()

        while True:
            # Get new logs since last check
            logs = daemon.get_run_logs(run_id, limit=100)

            for entry in logs.entries:
                if entry.timestamp > last_check:
                    yield f"data: {entry.json()}\n\n"

            last_check = datetime.now()

            # Check if run is still active
            if daemon.current_run and daemon.current_run.run_id == run_id:
                await asyncio.sleep(1)  # Check every second while running
            else:
                # Run completed, send final event
                yield f"data: {{\"event\": \"completed\"}}\n\n"
                break

    return StreamingResponse(generate(), media_type="text/event-stream")


# ==================== WebSocket for Real-time Updates ====================


@router.websocket("/ws/status")
async def websocket_status(
    websocket: WebSocket,
    daemon: RFPDaemon = Depends(get_rfp_daemon)
):
    """WebSocket endpoint for real-time daemon status updates"""
    await websocket.accept()

    try:
        while True:
            # Send current status
            status = daemon.get_status()
            await websocket.send_json(status.dict())

            # Wait before next update
            await asyncio.sleep(5)  # Update every 5 seconds

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


@router.websocket("/ws/run/{run_id}")
async def websocket_run_progress(
    websocket: WebSocket,
    run_id: str,
    daemon: RFPDaemon = Depends(get_rfp_daemon)
):
    """WebSocket endpoint for real-time run progress"""
    await websocket.accept()

    try:
        while True:
            # Check if this run is active
            if daemon.current_run and daemon.current_run.run_id == run_id:
                # Send current progress
                await websocket.send_json({
                    "run_id": run_id,
                    "status": daemon.current_run.status.value,
                    "progress": {
                        "found": daemon.current_run.total_found,
                        "processed": daemon.current_run.total_processed,
                        "qualified": daemon.current_run.total_qualified,
                        "maybe": daemon.current_run.total_maybe,
                        "rejected": daemon.current_run.total_rejected,
                        "errors": daemon.current_run.total_errors
                    }
                })

                await asyncio.sleep(1)  # Update every second
            else:
                # Run completed or not found
                for run in daemon.recent_runs:
                    if run.run_id == run_id:
                        await websocket.send_json({
                            "run_id": run_id,
                            "status": "completed",
                            "final_results": run.dict()
                        })
                        break
                else:
                    await websocket.send_json({
                        "run_id": run_id,
                        "status": "not_found"
                    })

                await websocket.close()
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for run {run_id}")
    except Exception as e:
        logger.error(f"WebSocket error for run {run_id}: {e}")
        await websocket.close()


# ==================== Default Schedule Setup ====================


@router.post("/setup/default-schedule")
async def setup_default_schedule(daemon: RFPDaemon = Depends(get_rfp_daemon)):
    """Set up the default 5PM daily schedule"""
    try:
        # Create default search config
        search_config = RFPSearchRequest(
            search_keywords=[
                'artificial intelligence',
                'machine learning',
                'data analytics',
                'automation',
                'software development',
                'cloud computing'
            ],
            days_back=3,
            max_rfps=200,
            model_name="llama-3.1-70b",  # Default Kamiwaza model
            batch_size=10,
            include_naics=['541511', '541512', '541519', '518210'],
            exclude_keywords=['janitorial', 'food service', 'construction']
        )

        # Create 5PM daily schedule
        schedule = RFPSchedule(
            schedule_id="daily_5pm",
            name="Daily 5PM Discovery",
            cron_expression="0 17 * * *",  # 5PM every day
            enabled=True,
            search_config=search_config
        )

        schedule_id = daemon.add_schedule(schedule)

        return {
            "status": "created",
            "schedule_id": schedule_id,
            "message": "Default 5PM daily schedule has been set up"
        }

    except Exception as e:
        logger.error(f"Failed to set up default schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Settings Management ====================


@router.get("/settings", response_model=Settings)
async def get_settings():
    """Get current application settings"""
    try:
        service = get_settings_service()
        return service.get_settings()
    except Exception as e:
        logger.error(f"Failed to get settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings", response_model=Settings)
async def update_settings(settings: Settings):
    """Update application settings"""
    try:
        service = get_settings_service()
        updated = service.update_settings(settings)
        logger.info("Settings updated successfully")
        return updated
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/validate")
async def validate_settings():
    """Validate current settings configuration"""
    try:
        service = get_settings_service()
        validation = service.validate_settings()
        return validation
    except Exception as e:
        logger.error(f"Failed to validate settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))