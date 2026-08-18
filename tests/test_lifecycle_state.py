from kalshi_bot.execution.state import (
    LifecycleState,
    clear_lifecycle_state,
    load_lifecycle_state,
    save_lifecycle_state,
)


def test_load_lifecycle_state_returns_previously_persisted_session(
    tmp_path,
) -> None:
    state_path = tmp_path / "lifecycle-state.json"
    state_path.write_text(
        """
        {
          "client_order_id_prefix": "kbot-previous-session-",
          "ticker": "TEST-MARKET"
        }
        """,
        encoding="utf-8",
    )

    result = load_lifecycle_state(state_path)

    assert result == LifecycleState(
        client_order_id_prefix="kbot-previous-session-",
        ticker="TEST-MARKET",
    )


def test_save_lifecycle_state_persists_session_for_restart(
    tmp_path,
) -> None:
    state_path = tmp_path / "lifecycle-state.json"
    lifecycle_state = LifecycleState(
        client_order_id_prefix="kbot-current-session-",
        ticker="TEST-MARKET",
    )

    save_lifecycle_state(
        lifecycle_state,
        state_path=state_path,
    )

    assert load_lifecycle_state(state_path) == lifecycle_state


def test_clear_lifecycle_state_removes_persisted_session(
    tmp_path,
) -> None:
    state_path = tmp_path / "lifecycle-state.json"
    lifecycle_state = LifecycleState(
        client_order_id_prefix="kbot-completed-session-",
        ticker="TEST-MARKET",
    )
    save_lifecycle_state(
        lifecycle_state,
        state_path=state_path,
    )

    clear_lifecycle_state(state_path)

    assert not state_path.exists()
