"""Print-job queue for the local connector. No Flask coupling.

Jobs carry fully-resolved ZPL (dates already substituted at submit time);
the agent is a dumb pipe to the printer. Claiming marks jobs `sent` so a
second poll doesn't print duplicates; a job stuck in `sent` after an agent
crash stays visible in the user's job list for manual re-submission.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.print_job import PrintJob, PrintJobStatus


class PrintJobNotFoundError(LookupError):
    pass


def create_job(
    session: Session,
    *,
    device_id: int,
    created_by: int,
    printer: str,
    zpl: str,
    copies: int = 1,
) -> PrintJob:
    job = PrintJob(
        device_id=device_id, created_by=created_by, printer=printer, zpl=zpl, copies=copies
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def list_jobs_for_user(session: Session, *, user_id: int, limit: int = 50) -> list[PrintJob]:
    stmt = (
        select(PrintJob)
        .where(PrintJob.created_by == user_id)
        .order_by(PrintJob.created_at.desc(), PrintJob.id.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt))


def claim_pending_jobs(session: Session, *, device_id: int, limit: int = 20) -> list[PrintJob]:
    """Return pending jobs for the device, marking them `sent` atomically
    within this transaction so repeated polls don't double-print."""
    stmt = (
        select(PrintJob)
        .where(PrintJob.device_id == device_id, PrintJob.status == PrintJobStatus.PENDING)
        .order_by(PrintJob.created_at, PrintJob.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    jobs = list(session.scalars(stmt))
    now = datetime.now(UTC)
    for job in jobs:
        job.status = PrintJobStatus.SENT
        job.sent_at = now
    session.commit()
    return jobs


def report_status(
    session: Session,
    job_id: int,
    *,
    device_id: int,
    status: PrintJobStatus,
    error: str | None = None,
) -> PrintJob:
    job = session.get(PrintJob, job_id)
    if job is None or job.device_id != device_id:
        raise PrintJobNotFoundError(job_id)
    job.status = status
    job.error = error
    job.finished_at = datetime.now(UTC)
    session.commit()
    session.refresh(job)
    return job
