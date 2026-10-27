from typing import Protocol


class Funder(Protocol):
    def hold(self, payment) -> str:
        """Secure the buyer's money for this payment and return a reference."""
        ...

    def release(self, payment) -> str:
        """Pay the seller from the held money and return a reference."""
        ...

    def refund(self, payment) -> str:
        """Give the held money back to the buyer and return a reference."""
        ...


class SimulatedFunder:
    """Pretends to move the money. No PayPal call is made.

    TEMPORARY: replaced by a PayPal sandbox funder once the buyer-approval
    flow is built. Every reference starts with SIM- so it can never be
    mistaken for a real one.
    """

    def hold(self, payment) -> str:
        return f"SIM-FUND-{payment.id}"

    def release(self, payment) -> str:
        return f"SIM-PAYOUT-{payment.id}"

    def refund(self, payment) -> str:
        return f"SIM-REFUND-{payment.id}"
