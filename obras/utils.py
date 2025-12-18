from typing import Dict, Iterable, Optional

from .models import Obra, ObraSnapshot


def calculate_progress_milestones(
    obra: Obra,
    snapshots: Iterable[ObraSnapshot],
    thresholds=None,
) -> Dict[int, Optional[int]]:
    if thresholds is None:
        thresholds = [0, 10, 20, 30, 50, 100]

    snapshots = list(snapshots)
    snapshots.sort(key=lambda s: s.data)

    start_date = obra.data_inicio or (snapshots[0].data if snapshots else None)
    milestones: Dict[int, Optional[int]] = {int(t): None for t in thresholds}

    if start_date is not None and 0 in milestones:
        milestones[0] = 0

    if not start_date:
        return milestones

    remaining = [t for t in thresholds if t != 0]
    for snap in snapshots:
        pct = float(snap.percentual_real)
        for t in list(remaining):
            if pct >= t:
                milestones[int(t)] = (snap.data - start_date).days
                remaining.remove(t)
        if not remaining:
            break

    return milestones

