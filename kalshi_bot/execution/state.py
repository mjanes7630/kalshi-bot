import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LifecycleState:
    client_order_id_prefix: str
    ticker: str
    submitted_order_ids: tuple[str, ...] = ()


def load_lifecycle_state(state_path: Path) -> LifecycleState:
    state_data = json.loads(state_path.read_text(encoding="utf-8"))

    return LifecycleState(
        client_order_id_prefix=state_data["client_order_id_prefix"],
        ticker=state_data["ticker"],
        submitted_order_ids=tuple(
            state_data.get("submitted_order_ids", []),
        ),
    )


def save_lifecycle_state(
    lifecycle_state: LifecycleState,
    *,
    state_path: Path,
) -> None:
    state_data = {
        "client_order_id_prefix": lifecycle_state.client_order_id_prefix,
        "ticker": lifecycle_state.ticker,
        "submitted_order_ids": list(lifecycle_state.submitted_order_ids),
    }

    state_path.write_text(
        json.dumps(state_data),
        encoding="utf-8",
    )


def record_submitted_order_id(
    *,
    order_id: str,
    state_path: Path,
) -> None:
    lifecycle_state = load_lifecycle_state(state_path)

    updated_lifecycle_state = LifecycleState(
        client_order_id_prefix=lifecycle_state.client_order_id_prefix,
        ticker=lifecycle_state.ticker,
        submitted_order_ids=(
            *lifecycle_state.submitted_order_ids,
            order_id,
        ),
    )

    save_lifecycle_state(
        updated_lifecycle_state,
        state_path=state_path,
    )


def clear_lifecycle_state(state_path: Path) -> None:
    state_path.unlink()


def remove_submitted_order_id(
    *,
    order_id: str,
    state_path: Path,
) -> None:
    lifecycle_state = load_lifecycle_state(state_path)

    updated_lifecycle_state = LifecycleState(
        client_order_id_prefix=lifecycle_state.client_order_id_prefix,
        ticker=lifecycle_state.ticker,
        submitted_order_ids=tuple(
            submitted_order_id
            for submitted_order_id in lifecycle_state.submitted_order_ids
            if submitted_order_id != order_id
        ),
    )

    save_lifecycle_state(
        updated_lifecycle_state,
        state_path=state_path,
    )
