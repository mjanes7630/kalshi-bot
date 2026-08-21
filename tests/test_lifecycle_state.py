from kalshi_bot.execution.state import (
    LifecycleState,
    clear_lifecycle_state,
    load_lifecycle_state,
    record_submitted_order_id,
    remove_submitted_order_id,
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


def test_save_lifecycle_state_persists_submitted_order_ids(
    tmp_path,
) -> None:
    state_path = tmp_path / "lifecycle-state.json"
    lifecycle_state = LifecycleState(
        client_order_id_prefix="kbot-current-session-",
        ticker="TEST-MARKET",
        submitted_order_ids=(
            "order-123",
            "order-456",
        ),
    )

    save_lifecycle_state(
        lifecycle_state,
        state_path=state_path,
    )

    assert load_lifecycle_state(state_path) == lifecycle_state


def test_record_submitted_order_id_updates_persisted_lifecycle_state(
    tmp_path,
) -> None:
    state_path = tmp_path / "lifecycle-state.json"
    save_lifecycle_state(
        LifecycleState(
            client_order_id_prefix="kbot-current-session-",
            ticker="TEST-MARKET",
        ),
        state_path=state_path,
    )

    record_submitted_order_id(
        order_id="order-123",
        state_path=state_path,
    )

    assert load_lifecycle_state(state_path) == LifecycleState(
        client_order_id_prefix="kbot-current-session-",
        ticker="TEST-MARKET",
        submitted_order_ids=("order-123",),
    )


def test_remove_submitted_order_id_updates_persisted_lifecycle_state(
    tmp_path,
) -> None:
    state_path = tmp_path / "lifecycle-state.json"

    save_lifecycle_state(
        LifecycleState(
            client_order_id_prefix="kbot-session-1234-",
            ticker="TEST-MARKET",
            submitted_order_ids=(
                "first-order-id",
                "second-order-id",
            ),
        ),
        state_path=state_path,
    )

    remove_submitted_order_id(
        order_id="first-order-id",
        state_path=state_path,
    )

    assert load_lifecycle_state(state_path) == LifecycleState(
        client_order_id_prefix="kbot-session-1234-",
        ticker="TEST-MARKET",
        submitted_order_ids=("second-order-id",),
    )
