"""Scheduler das verificações automáticas."""
from __future__ import annotations

import atexit

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

_scheduler = None


def iniciar_scheduler(app):
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    from app.services.notificacoes import verificar_e_enviar_alertas

    _scheduler = BackgroundScheduler(timezone='America/Sao_Paulo')
    _scheduler.add_job(
        func=verificar_e_enviar_alertas,
        args=[app],
        trigger=CronTrigger(hour=8, minute=0),
        id='alerta_validade_diario',
        name='Verificação diária de validade',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    atexit.register(_shutdown_scheduler)
    app.logger.info('[Scheduler] Verificação diária agendada para 08:00.')
    return _scheduler


def _shutdown_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
