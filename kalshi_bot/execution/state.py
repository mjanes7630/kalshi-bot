import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LifecycleState:
    client_order_id_prefix: str
    ticker: str


def load_lifecycle_state(state_path: Path) -> LifecycleState:
    state_data = json.loads(state_path.read_text(encoding="utf-8"))

    return LifecycleState(
        client_order_id_prefix=state_data["client_order_id_prefix"],
        ticker=state_data["ticker"],
    )


def save_lifecycle_state(
    lifecycle_state: LifecycleState,
    *,
    state_path: Path,
) -> None:
    state_data = {
        "client_order_id_prefix": lifecycle_state.client_order_id_prefix,
        "ticker": lifecycle_state.ticker,
    }

    state_path.write_text(
        json.dumps(state_data),
        encoding="utf-8",
    )


def clear_lifecycle_state(state_path: Path) -> None:
    state_path.unlink()
