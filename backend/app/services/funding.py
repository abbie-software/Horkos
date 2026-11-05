from dataclasses import dataclass
from typing import Protocol


class FundingError(Exception):
    """The payment provider could not do what was asked."""


class NotApprovedYet(FundingError):
    """The buyer has not approved the payment on PayPal yet."""


@dataclass(frozen=True)
class FundingStart:
    """What happened when funding began.

    held=True means the money is already held and ref is the authorization.
    held=False means the buyer still has to approve it: ref is the PayPal
    order and approve_url is where the buyer goes to do that.
    """

    ref: str
    held: bool
    approve_url: str | None = None


class Funder(Protocol):
    def start(self, payment, seller) -> FundingStart:
        """Begin securing the buyer's money for this payment."""
        ...

    def confirm(self, payment) -> str:
        """After the buyer approved: place the hold and return its reference."""
        ...

    def capture(self, payment) -> str:
        """Take the held money, ready to pay the seller. Returns a reference."""
        ...

    def payout(self, payment, seller) -> str:
        """Pay the seller. Returns a reference."""
        ...

    def refund(self, payment) -> str:
        """Give the buyer their money back. Returns a reference."""
        ...


class SimulatedFunder:
    """Pretends to move the money. No PayPal call is made.

    Every reference starts with SIM- so it can never be mistaken for a real one.
    """

    def start(self, payment, seller) -> FundingStart:
        return FundingStart(ref=f"SIM-FUND-{payment.id}", held=True)

    def confirm(self, payment) -> str:
        return f"SIM-FUND-{payment.id}"

    def capture(self, payment) -> str:
        return f"SIM-CAPTURE-{payment.id}"

    def payout(self, payment, seller) -> str:
        return f"SIM-PAYOUT-{payment.id}"

    def refund(self, payment) -> str:
        return f"SIM-REFUND-{payment.id}"
