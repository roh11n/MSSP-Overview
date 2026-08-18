"""APScheduler-driven automated PPTX email reports.

Weekly (Mon 08:00 UTC) and monthly (1st 08:00 UTC) cron jobs scan
`db.report_schedules` for enabled entries and email each one a freshly-built
PPTX deck via the existing emailer (console-mock unless SMTP_* env is set).
"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import emailer
import llm as llm_mod
import pptx_export
import recommendations
import tenants as tenants_mod

logger = logging.getLogger("mssp-soc.scheduler")

_scheduler = None


async def _get_tenant(db, tenant_id):
    t = await db.tenants.find_one({"id": tenant_id or "all"}, {"_id": 0})
    if not t:
        return {"id": "all", "name": "All Tenants", "domain": "ALL", "primary_color": "#3B82F6", "logo_url": None}
    return t


async def _send_one(db, sch: dict) -> dict:
    period = sch.get("period", "monthly")
    tenant_id = sch.get("tenant_id", "all")
    tenant = await _get_tenant(db, tenant_id)

    all_data = tenants_mod.all_dashboards(period, tenant)
    recs = recommendations.generate(
        all_data["executive"], all_data["soc_manager"], all_data["detection"],
        all_data["threat_intel"], all_data["soar"],
    )
    recs = llm_mod.enrich_recommendations(recs, all_data["executive"], max_llm=2)
    buf = pptx_export.build_pptx(tenant, period, all_data, recs)

    subject = sch.get("subject") or f"MSSP SOC Report — {tenant.get('name', 'All Tenants')} ({period})"
    html = (
        f"<p>Automated <b>{sch.get('frequency')}</b> SOC KPI report for "
        f"<b>{tenant.get('name', 'All Tenants')}</b> ({period}).</p>"
        f"<p>The PPTX deck is attached. Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.</p>"
    )
    res = await emailer.send_email(
        db,
        to=list(sch.get("recipients", [])),
        subject=subject,
        html=html,
        attachments=[{"filename": f"MSSP_SOC_{tenant.get('id', 'all')}_{period}.pptx", "data": buf.getvalue()}],
        meta={"scheduled": True, "schedule_id": sch.get("id"), "frequency": sch.get("frequency"),
              "tenant_id": tenant_id, "period": period},
    )
    await db.report_schedules.update_one(
        {"id": sch.get("id")},
        {"$set": {"last_run": datetime.now(timezone.utc).isoformat(), "last_status": res.get("mode")}},
    )
    logger.info("Scheduled report sent: schedule=%s tenant=%s mode=%s", sch.get("id"), tenant_id, res.get("mode"))
    return res


async def _run_due(db, frequency: str):
    schedules = await db.report_schedules.find(
        {"enabled": True, "frequency": frequency}
    ).to_list(500)
    logger.info("Running %d %s report schedule(s)", len(schedules), frequency)
    for sch in schedules:
        try:
            await _send_one(db, sch)
        except Exception:
            logger.exception("Scheduled report failed for schedule %s", sch.get("id"))


async def run_now(db, schedule_id: str) -> dict:
    """Trigger a single schedule immediately (used by the run-now endpoint)."""
    sch = await db.report_schedules.find_one({"id": schedule_id})
    if not sch:
        raise ValueError("Schedule not found")
    return await _send_one(db, sch)


def start(db):
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        _run_due, CronTrigger(day_of_week="mon", hour=8, minute=0),
        args=[db, "weekly"], id="weekly_reports", replace_existing=True,
    )
    _scheduler.add_job(
        _run_due, CronTrigger(day=1, hour=8, minute=0),
        args=[db, "monthly"], id="monthly_reports", replace_existing=True,
    )
    _scheduler.start()
    logger.info("Report scheduler started (weekly Mon 08:00 UTC, monthly 1st 08:00 UTC)")
    return _scheduler


def shutdown():
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
