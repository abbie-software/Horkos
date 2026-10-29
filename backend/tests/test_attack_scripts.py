import sys

from app.services.attack_scripts import (
    ATTACK_TEST_CODE,
    ATTACKS,
    BAD_WORK_CODE,
    ScriptedAgent,
    ScriptedChecker,
    Step,
)
from app.services.buyer_agent import is_usable_test_code
from app.services.sandbox import run_in_sandbox


def local_command(name, workdir, image):
    """Runs the test harness as a plain process, with no Docker needed."""
    return [sys.executable, "-I", f"{workdir}/harness.py", workdir]


def run_against(solution):
    return run_in_sandbox(
        solution,
        ATTACK_TEST_CODE,
        timeout_seconds=10.0,
        build=local_command,
        stop=lambda name: None,
    )


def test_the_six_attacks_from_the_contract_exist():
    assert set(ATTACKS) == {
        "recipient_change",
        "over_limit",
        "edge_of_limit",
        "rapid_retries",
        "pressure_language",
        "bad_work",
    }


def test_every_attack_announces_itself_in_the_mock_wording():
    for script in ATTACKS.values():
        assert script.message.startswith("Red Team: ")
    assert ATTACKS["recipient_change"].message == (
        "Red Team: attempting to change the recipient mid-job."
    )


def test_rapid_retries_is_two_blocked_attempts_then_a_small_retry():
    amounts = [step.amount_cents for step in ATTACKS["rapid_retries"].steps]
    assert amounts == [50000, 45000, 500]
    assert all(amount > 5000 for amount in amounts[:2])  # over the $50 cap


def test_only_the_bad_work_attack_hands_in_code():
    handing_in = [name for name, s in ATTACKS.items() if s.hand_in_bad_work]
    assert handing_in == ["bad_work"]


def test_the_recipient_attack_names_a_different_account():
    (step,) = ATTACKS["recipient_change"].steps
    assert step.recipient_email == "attacker@example.com"
    assert all(s.recipient_email is None for n, a in ATTACKS.items()
               if n != "recipient_change" for s in a.steps)


def test_the_bad_work_passes_one_test_and_fails_two():
    result = run_against(BAD_WORK_CODE)
    assert result.status == "failed"
    assert (result.passed, result.failed, result.total) == (1, 2, 3)


def test_correct_work_would_pass_all_three_tests():
    result = run_against("def double(n):\n    return n * 2\n")
    assert result.status == "passed"
    assert result.total == 3


def test_the_scripted_test_file_is_a_usable_test_file():
    assert is_usable_test_code(ATTACK_TEST_CODE)


def test_the_scripted_agent_proposes_exactly_what_the_step_says():
    step = Step("Write a thing.", 1234, "sel_zed", "A thing.")
    proposal = ScriptedAgent(step).propose("anything")
    assert proposal.amount_cents == 1234
    assert proposal.category == "coding"
    assert proposal.description == "A thing."
    assert proposal.test_code == ATTACK_TEST_CODE
    assert len(proposal.acceptance_tests) == 4


def test_the_scripted_checker_never_objects():
    assert ScriptedChecker().check("x", "y").mismatch is False
