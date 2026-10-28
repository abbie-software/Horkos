from app.schemas.payments import DecisionOut
from app.services.messages import (
    BLOCK_NOTES,
    check_audit_reason,
    check_event_message,
    status_message,
    trust_audit_reason,
    trust_message,
    verdict_message,
)
from app.services.sandbox import SandboxResult


def decision(verdict, level="low", score=10, hard_rule=None):
    return DecisionOut(
        verdict=verdict,
        risk_score=score,
        risk_level=level,
        reason="x",
        hard_rule=hard_rule,
        signals=[],
    )


def test_verdict_messages_match_the_mock_wording():
    assert verdict_message(decision("approve")) == "Guard approved the payment (low risk)."
    assert verdict_message(decision("ask", "medium", 48)) == "Guard asked you to decide."
    blocked = decision("block", "high", 97, "recipient_changed")
    assert verdict_message(blocked) == (
        "Guard blocked the payment: recipient changed mid-job."
    )


def test_a_block_without_a_hard_rule_names_the_risk_score():
    assert verdict_message(decision("block", "high", 80)) == (
        "Guard blocked the payment: the risk score is 80 out of 100."
    )


def test_every_hard_rule_has_a_block_note():
    assert set(BLOCK_NOTES) == {
        "recipient_changed",
        "over_cap",
        "excluded_category",
        "blocklisted_or_low_trust",
    }


def test_status_messages():
    assert status_message("held", "Kip Codes", 1500) == "Funds are being held."
    assert status_message("released", "Kip Codes", 1500) == "Kip Codes was paid $15.00."
    assert status_message("refunded", "Kip Codes", 2000) == "$20.00 was refunded to the buyer."
    assert status_message("awaiting_user", "Zed Dev", 2500) == "Waiting for your decision."
    assert status_message("mystery", "Zed Dev", 100) == "Payment is now mystery."


def test_check_messages_for_good_and_wrong_work():
    good = SandboxResult(status="passed", passed=3, total=3)
    assert check_event_message(good) == "Work passed 3 of 3 tests."
    assert check_audit_reason(good) == "3 of 3 tests passed."

    wrong = SandboxResult(status="failed", passed=1, failed=2, total=3)
    assert check_event_message(wrong) == "Work failed: 1 of 3 tests passed."
    assert check_audit_reason(wrong) == (
        "1 of 3 tests passed. The work did not meet the agreed tests."
    )


def test_check_messages_when_there_are_no_test_counts():
    broken = SandboxResult(status="failed", output_excerpt="The work could not be loaded: X.")
    assert check_event_message(broken) == "Work failed: The work could not be loaded: X."
    assert check_audit_reason(broken) == "The work could not be loaded: X."


def test_trust_messages_match_the_mock_wording():
    assert trust_message("Kip Codes", 46, 58, 2500) == (
        "Kip Codes's trust rose from 46 to 58. New limit: $25.00."
    )
    assert trust_message("QuickPay Dev", 31, 9, 500) == (
        "QuickPay Dev's trust dropped from 31 to 9. New limit: $5.00."
    )
    assert trust_audit_reason("QuickPay Dev", 31, 9, 500) == (
        "QuickPay Dev's trust score dropped from 31 to 9 and the limit is now $5.00."
    )
