from typing import Any, Dict, Iterable, Optional

from django.db.models import Avg, Count, Q
from django.utils import timezone

from accounts.utils import filter_obras_for_user
from .models import Categoria, Obra, Tarefa


def get_last_accessible_obra(user) -> Optional[Obra]:
    """Retorna a obra mais recente disponivel para o usuario, priorizando as ativas."""
    base_qs = filter_obras_for_user(
        Obra.objects.prefetch_related("categorias__tarefas"),
        user,
    )
    ordered_qs = base_qs.order_by("-criado_em", "-id")
    last_active = ordered_qs.filter(status="ativa").first()
    if last_active:
        return last_active
    return ordered_qs.first()


def generate_duplicate_name(original_name: str) -> str:
    sufixo = " (copia)"
    base_nome = (original_name or "").strip()
    field = Obra._meta.get_field("nome")
    max_len = getattr(field, "max_length", None)
    if max_len:
        limite = max_len - len(sufixo)
        if limite < 0:
            limite = 0
        if len(base_nome) > limite:
            base_nome = base_nome[:limite].rstrip()
    return f"{base_nome}{sufixo}" if base_nome else "Nova obra (copia)"


def clone_obra_structure(source: Obra, target: Obra) -> None:
    for categoria in source.categorias.all():
        nova_categoria = Categoria.objects.create(
            obra=target,
            nome=categoria.nome,
            descricao=categoria.descricao,
            prazo_final=categoria.prazo_final,
            status=categoria.status,
        )
        tarefas = []
        for tarefa in categoria.tarefas.all():
            tarefas.append(
                Tarefa(
                    categoria=nova_categoria,
                    nome=tarefa.nome,
                    descricao=tarefa.descricao,
                    ordem=tarefa.ordem,
                    data_inicio_prevista=tarefa.data_inicio_prevista,
                    data_fim_prevista=tarefa.data_fim_prevista,
                    data_fim_real=None,
                    status="nao_iniciada",
                    percentual_concluido=0,
                )
            )
        if tarefas:
            Tarefa.objects.bulk_create(tarefas)


def _clamp_percentage(value: float) -> float:
    return max(0.0, min(value, 100.0))


def calculate_expected_progress(obra: Obra, reference_date=None) -> Optional[float]:
    if reference_date is None:
        reference_date = timezone.now().date()
    if not obra.data_inicio or not obra.data_fim_prevista:
        return None

    start = obra.data_inicio
    end = obra.data_fim_prevista
    if reference_date < start:
        return 0.0
    if reference_date > end:
        return 100.0

    total_days = (end - start).days
    if total_days <= 0:
        return 100.0 if reference_date >= end else 0.0

    days_passed = (reference_date - start).days
    percentual = (days_passed / total_days) * 100
    return round(_clamp_percentage(percentual), 1)


def get_obras_progress_snapshot(obras: Iterable[Obra]) -> Dict[int, Dict[str, Any]]:
    obras = list(obras)
    if not obras:
        return {}

    obra_ids = [obra.id for obra in obras]
    tarefa_stats = (
        Tarefa.objects
        .filter(categoria__obra_id__in=obra_ids)
        .values("categoria__obra_id")
        .annotate(
            total=Count("id"),
            concluidas=Count("id", filter=Q(status="concluida")),
            avg_percentual=Avg("percentual_concluido"),
            tarefas_com_percentual=Count("id", filter=~Q(percentual_concluido__in=[0, 100])),
        )
    )
    stats_map = {item["categoria__obra_id"]: item for item in tarefa_stats}
    reference_date = timezone.now().date()

    snapshot = {}
    for obra in obras:
        obra_stats = stats_map.get(obra.id, {})
        total = obra_stats.get("total") or 0
        concluidas = obra_stats.get("concluidas") or 0
        avg_percentual = obra_stats.get("avg_percentual")
        has_partial_progress = bool(obra_stats.get("tarefas_com_percentual"))

        if avg_percentual is not None and has_partial_progress:
            progresso_real = float(avg_percentual)
        elif total:
            progresso_real = (concluidas / total) * 100
        else:
            progresso_real = 0.0

        progresso_real = round(_clamp_percentage(progresso_real), 1)
        progresso_esperado = calculate_expected_progress(obra, reference_date)
        sem_tarefas = total == 0

        delta = None
        status_label = None
        badge_class = None
        if progresso_esperado is not None:
            delta = round(progresso_real - progresso_esperado, 1)
            if delta >= 2:
                status_label = "Adiantado"
                badge_class = "bg-success"
            elif delta >= 0:
                status_label = "No prazo"
                badge_class = "bg-primary"
            else:
                status_label = "Atrasado"
                badge_class = "bg-danger"

        snapshot[obra.id] = {
            "real": progresso_real,
            "expected": progresso_esperado,
            "sem_tarefas": sem_tarefas,
            "delta": delta,
            "status_label": status_label,
            "badge_class": badge_class,
        }

    return snapshot
