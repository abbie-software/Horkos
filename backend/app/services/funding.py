from typing import Protocol


class Funder(Protocol):
    def hold(self, payment) -> str:
        """Secure the buyer's money for this payment and return a reference."""
        ...


class SimulatedFunder:
    """Pretends to hold the money. No PayPal call is made.

    TEMPORARY: replaced by a PayPal sandbox funder once the buyer-approval
    flow is built. The reference always starts with SIM- so it can never be
    mistaken for a real one.
    """

    def hold(self, payment) -> str:
        return f"SIM-FUND-{payment.id}"