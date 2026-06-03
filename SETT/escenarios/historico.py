"""
Seed historico: ~90 dias de incidentes TERMINADOS (atendido / cancelado) con
fechas EXPLICITAS en el pasado para poblar los KPIs por rango temporal.

Por que existe:
  Los KPIs (app/services/kpi_service.py y admin/ganancias) filtran por las
  columnas created_at / updated_at de las ENTIDADES (Incidente, Asignacion,
  Pago, Evaluacion) y por el created_at del historial de asignacion, NO por la
  tabla Metrica. Una base recien sembrada solo tiene escenarios "de hoy", asi
  que toda consulta por rango (ultimos 30/60/90 dias) devuelve vacio. Este
  modulo genera volumen historico con fechas reales en el pasado.

Reglas (alineadas con las correcciones 1.4 y 1.5):
  - Solo estados TERMINALES (atendido/cancelado). NUNCA deja incidentes
    'pendiente' activos que disparen la regla "1 incidente activo por usuario"
    (409); los estados activos los proveen los escenarios e01-e05 en vivo.
  - Determinista (random.Random con semilla fija) para reproducibilidad.
  - Distribucion ponderada hacia el primer taller (mas volumen).
  - Un commit por dia para no acumular toda la historia en memoria.

Es defensivo: run_all lo invoca dentro de try/except (no es fatal si falla).
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.incidente import (
    Asignacion,
    Evaluacion,
    HistorialEstadoAsignacion,
    HistorialEstadoIncidente,
    Incidente,
)
from app.models.transaccional import Metrica, Pago
from SETT.utils import Ctx, logger


DIAS_HISTORIA = 90
SEED = 20240101

# Reparto de volumen por taller (indice en ctx.talleres): el primero recibe mas.
PESOS_TALLER = [0.6, 0.25, 0.15]

CATEGORIAS_POOL = ["bateria", "llanta", "motor", "choque", "llaves", "otros"]
PRIORIDADES_POOL = ["baja", "media", "alta", "critica"]
METODOS_POOL = ["tarjeta", "transferencia", "efectivo", "qr"]

COMENTARIOS = [
    "Excelente servicio, muy rapidos.",
    "Buen trabajo, lo recomiendo.",
    "Atencion correcta.",
    "Tecnico amable y profesional.",
    "Resolvieron el problema sin demoras.",
]


def _hist_inc(db: Session, inc_id: int, anterior, nuevo, obs: str, ts: datetime) -> None:
    db.add(HistorialEstadoIncidente(
        id_incidente=inc_id,
        id_estado_anterior=anterior,
        id_estado_nuevo=nuevo,
        observacion=obs,
        created_at=ts,
    ))


def _hist_asig(db: Session, asig_id: int, anterior, nuevo, obs: str, ts: datetime) -> None:
    db.add(HistorialEstadoAsignacion(
        id_asignacion=asig_id,
        id_estado_anterior=anterior,
        id_estado_nuevo=nuevo,
        observacion=obs,
        created_at=ts,
    ))


def run(db: Session, ctx: Ctx) -> None:
    if not ctx.talleres or not ctx.clientes:
        logger.info("[historico] sin talleres/clientes en ctx, se omite")
        return

    rnd = random.Random(SEED)

    e_inc = ctx.estado_incidente
    e_asig = ctx.estado_asignacion

    client_keys = list(ctx.clientes.keys())
    n_talleres = len(ctx.talleres)
    # Pesos robustos: si hay mas talleres que pesos definidos, el resto recibe 0.1.
    pesos = [PESOS_TALLER[i] if i < len(PESOS_TALLER) else 0.1 for i in range(n_talleres)]

    ahora = datetime.now(timezone.utc)
    total = 0

    for dia in range(DIAS_HISTORIA, 0, -1):
        base_dia = ahora - timedelta(days=dia)

        for _ in range(rnd.randint(2, 4)):
            tk = rnd.choices(range(n_talleres), weights=pesos)[0]
            taller = ctx.talleres[tk]
            id_tenant = taller.id_tenant

            # Tecnicos del taller: el seed crea 2 por taller en orden (indices 2k, 2k+1).
            idxs = [2 * tk, 2 * tk + 1]
            tecnicos_taller = [ctx.tecnicos[i] for i in idxs if i < len(ctx.tecnicos)]
            tecnico = rnd.choice(tecnicos_taller) if tecnicos_taller else None

            ckey = rnd.choice(client_keys)
            cliente = ctx.clientes[ckey]
            vehiculo = ctx.vehiculos[ckey]

            categoria = rnd.choice(CATEGORIAS_POOL)
            prioridad = rnd.choice(PRIORIDADES_POOL)
            lat = -17.78 - rnd.random() * 0.06
            lng = -63.16 - rnd.random() * 0.06

            # Fecha base del incidente: hora coherente dentro del dia pasado.
            t0 = base_dia.replace(
                hour=rnd.randint(7, 20),
                minute=rnd.randint(0, 59),
                second=0,
                microsecond=0,
            )

            # Historico = solo incidentes TERMINADOS (completada / cancelada).
            r = rnd.random()
            completada = r < 0.85
            estado_inc = "atendido" if completada else "cancelado"
            estado_asig = "completada" if completada else "cancelada"

            # Tiempos derivados (coherentes y en el pasado).
            t_acept = t0 + timedelta(minutes=5)
            t_llegada = t0 + timedelta(minutes=20)
            t_fin = t0 + timedelta(minutes=rnd.randint(40, 90))

            # ── Incidente con fechas pasadas EXPLICITAS ──────────────────────
            inc = Incidente(
                id_tenant=id_tenant,
                id_usuario=cliente.id_usuario,
                id_vehiculo=vehiculo.id_vehiculo,
                id_estado=e_inc[estado_inc].id_estado,
                id_categoria=ctx.categoria[categoria].id_categoria,
                id_prioridad=ctx.prioridad[prioridad].id_prioridad,
                latitud=lat,
                longitud=lng,
                descripcion_usuario=f"[historico] {categoria}",
                resumen_ia=f"[historico] {categoria} ({prioridad})",
                clasificacion_ia_confianza=0.9,
                requiere_revision_manual=False,
                created_at=t0,
                updated_at=t_fin if completada else t_acept,
            )
            db.add(inc)
            db.flush()

            # ── Historial incidente ──────────────────────────────────────────
            _hist_inc(db, inc.id_incidente, None,
                      e_inc["pendiente"].id_estado, "Incidente reportado", t0)
            if completada:
                _hist_inc(db, inc.id_incidente, e_inc["pendiente"].id_estado,
                          e_inc["en_proceso"].id_estado, "En atencion", t_acept)
                _hist_inc(db, inc.id_incidente, e_inc["en_proceso"].id_estado,
                          e_inc["atendido"].id_estado, "Resuelto", t_fin)
            else:
                _hist_inc(db, inc.id_incidente, e_inc["pendiente"].id_estado,
                          e_inc["cancelado"].id_estado, "Cancelado por el cliente", t_acept)

            # ── Asignacion ───────────────────────────────────────────────────
            asig = Asignacion(
                id_tenant=id_tenant,
                id_incidente=inc.id_incidente,
                id_taller=taller.id_taller,
                id_usuario=tecnico.id_usuario if tecnico else None,
                id_estado_asignacion=e_asig[estado_asig].id_estado_asignacion,
                eta_minutos=15,
                created_at=t_acept,
                updated_at=t_fin if completada else t_acept,
                cancelada_at=None if completada else t_acept,
                motivo_cancelacion=None if completada else "Cliente cancelo la solicitud",
                cancelada_por=None if completada else "cliente",
            )
            db.add(asig)
            db.flush()

            # ── Historial asignacion (created_at progresivo) ─────────────────
            _hist_asig(db, asig.id_asignacion, None,
                       e_asig["pendiente"].id_estado_asignacion, "Motor selecciono taller", t0)
            if completada:
                _hist_asig(db, asig.id_asignacion, e_asig["pendiente"].id_estado_asignacion,
                           e_asig["aceptada"].id_estado_asignacion, "Aceptada", t_acept)
                _hist_asig(db, asig.id_asignacion, e_asig["aceptada"].id_estado_asignacion,
                           e_asig["en_camino"].id_estado_asignacion, "En camino",
                           t_acept + timedelta(minutes=3))
                _hist_asig(db, asig.id_asignacion, e_asig["en_camino"].id_estado_asignacion,
                           e_asig["llegado"].id_estado_asignacion, "Llegado", t_llegada)
                _hist_asig(db, asig.id_asignacion, e_asig["llegado"].id_estado_asignacion,
                           e_asig["completada"].id_estado_asignacion, "Completada", t_fin)
            else:
                _hist_asig(db, asig.id_asignacion, e_asig["pendiente"].id_estado_asignacion,
                           e_asig["cancelada"].id_estado_asignacion, "Cancelada", t_acept)

            # ── Metrica (timestamps coherentes con el estado) ────────────────
            metrica = Metrica(
                id_tenant=id_tenant,
                id_incidente=inc.id_incidente,
                fecha_inicio=t0,
            )
            if completada:
                metrica.fecha_asignacion = t_acept
                metrica.tiempo_respuesta_min = 5
                metrica.fecha_llegada_tecnico = t_llegada
                metrica.tiempo_llegada_min = 15
                metrica.fecha_fin = t_fin
                metrica.tiempo_resolucion_min = int((t_fin - t0).total_seconds() // 60)
            db.add(metrica)

            # ── Pago + Evaluacion (solo completadas) ─────────────────────────
            if completada:
                monto = round(rnd.uniform(70, 250), 2)
                db.add(Pago(
                    id_tenant=id_tenant,
                    id_incidente=inc.id_incidente,
                    id_metodo_pago=ctx.metodo_pago[rnd.choice(METODOS_POOL)].id_metodo_pago,
                    id_estado_pago=ctx.estado_pago["completado"].id_estado_pago,
                    tipo="servicio",
                    monto_total=monto,
                    comision_plataforma=round(monto * 0.10, 2),
                    monto_taller=round(monto * 0.90, 2),
                    referencia_externa=f"pi_hist_{inc.id_incidente}",
                    created_at=t_fin,
                    updated_at=t_fin,
                ))
                estrellas = rnd.choices([3, 4, 5], weights=[0.15, 0.35, 0.5])[0]
                db.add(Evaluacion(
                    id_tenant=id_tenant,
                    id_incidente=inc.id_incidente,
                    id_usuario=cliente.id_usuario,
                    id_taller=taller.id_taller,
                    estrellas=estrellas,
                    comentario=rnd.choice(COMENTARIOS),
                    created_at=t_fin,
                ))
                metrica.calificacion_cliente = estrellas

            total += 1

        # Un commit por dia: no acumula toda la historia en memoria.
        db.commit()

    logger.info(f"[historico] {total} incidentes terminales sembrados en {DIAS_HISTORIA} dias")
