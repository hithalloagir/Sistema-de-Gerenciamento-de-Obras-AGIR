from typing import Optional

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
