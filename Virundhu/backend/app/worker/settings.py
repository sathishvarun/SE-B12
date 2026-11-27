"""ARQ worker settings. Run with:  arq app.worker.settings.WorkerSettings"""

from arq import cron
from arq.connections import RedisSettings

from app.config import settings
from app.worker.jobs import (
    accounts_month_tick,
    agent_tick,
    analyze_job,
    daily_digest_tick,
    demo_prep_job,
    google_sync_tick,
    holding_reply_tick,
    monthly_report_tick,
    places_tick,
    plan_reminder_tick,
    reply_promise_tick,
    retention_tick,
    retry_unread_tick,
    weekly_summary_tick,
)


class WorkerSettings:
    """Functions the worker can run, plus scheduled jobs (times in UTC)."""

    functions = [analyze_job, demo_prep_job]
    cron_jobs = [
        cron(agent_tick, second={0}, run_at_startup=True),  # AI agent team: demos and support, every minute
        cron(retry_unread_tick, minute=set(range(0, 60, 5)), run_at_startup=True),  # re-read failed reviews
        cron(google_sync_tick, minute={0, 10, 20, 30, 40, 50}),  # live Google reviews
        cron(places_tick, minute=45),  # Google reviews by Maps listing (Places API), each outlet once a day
        cron(reply_promise_tick, minute=set(range(2, 60, 5))),  # 1-hour reply promise: reminders up the ladder
        cron(holding_reply_tick, minute={5, 20, 35, 50}),  # safe first reply to unanswered complaints (opt-in)
        cron(weekly_summary_tick, weekday=0, hour=3, minute=30),  # Monday 9:00 am India time
        cron(plan_reminder_tick, minute=25),  # trial/plan ending reminders
        cron(monthly_report_tick, day=1, hour=3, minute=0),  # 8:30 am India time on the 1st
        cron(accounts_month_tick, day=1, hour=2, minute=50),  # 8:20 am India time: accounts Excel to the accountant
        cron(daily_digest_tick, hour=15, minute=30),  # 9 pm India time: admin's daily summary
        cron(retention_tick, hour=21, minute=40),  # 3:10 am India time: delete data past its retention period
    ]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 900
