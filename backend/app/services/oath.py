import re
from decimal import Decimal

from app.schemas.oath import Policy


class OathParseError(ValueError):
    """The oath text is missing something Horkos needs in order to enforce it."""


MONEY = r"\$\s*(\d[\d,]*(?:\.\d{1,2})?)"
SEP = r"(?:\s*/\s*|\s+(?:per|a|an|each|every)\s+)"

PER_JOB = re.compile(MONEY + SEP + r"(?:job|task|project|payment|request)s?\b", re.IGNORECASE)
PER_DAY = re.compile(MONEY + r"(?:" + SEP + r"day|\s+daily)\b", re.IGNORECASE)
ASK_OVER = re.compile(
    r"\bask\b.*?\b(?:over|above|more than|exceeds?|exceeding|greater than)\s+" + MONEY,
    re.IGNORECASE,
)
NEVER_ASK = re.compile(r"\b(?:never|don't|do not|dont)\s+ask\b", re.IGNORECASE)
ASK_WORD = re.compile(r"\b(?:ask|approv\w*|confirm\w*|check)\b", re.IGNORECASE)
SELLER_WORD = re.compile(r"\bsellers?\b", re.IGNORECASE)
NEW_SELLER = re.compile(
    r"\b(?:new|unfamiliar|unknown|first[- ]time|not used|haven't used|have not used"
    r"|never used|not worked with|haven't worked with|have not worked with)\b",
    re.IGNORECASE,
)
ONLY = re.compile(
    r"\bonly\s+(?:(?:allow|on|for|spend on|pay for|hire for|buy)\s+)?"
    r"([a-z][a-z-]*)(?:\s+(work|jobs?|tasks?|projects?))?",
    re.IGNORECASE,
)
NEVER_CATEGORY = re.compile(
    r"\b(?:never|do not|don't|dont|no)\s+(?:spend\s+on|pay\s+for|buy|hire\s+for|allow)\s+"
    r"([a-z][a-z-]*)(?:\s+(work|jobs?|tasks?|projects?))?",
    re.IGNORECASE,
)

CATEGORY_WORDS = {
    "coding": "coding",
    "code": "coding",
    "programming": "coding",
    "software": "coding",
    "writing": "writing",
    "design": "design",
}


def to_cents(amount: str) -> int:
    return int((Decimal(amount.replace(",", "")) * 100).to_integral_value())


def resolve_category(word: str, has_suffix: bool) -> str | None:
    word = word.lower()
    if word in CATEGORY_WORDS:
        return CATEGORY_WORDS[word]
    return word if has_suffix else None


def add_unique(items: list[str], value: str | None) -> None:
    if value and value not in items:
        items.append(value)


def parse_policy(text: str) -> Policy:
    """Turn the oath's plain English into the rules Horkos enforces.

    Fixed pattern matching, not AI, so the same text always gives the same
    rules. If several limits are stated, the lowest one wins.
    """
    text = (text or "").strip()
    if not text:
        raise OathParseError("Write your oath first, for example: Spend up to $50 per job.")

    job_caps: list[int] = []
    day_caps: list[int] = []
    thresholds: list[int] = []
    allowed: list[str] = []
    blocked: list[str] = []
    ask_new_sellers = False

    def grab(match: re.Match) -> str:
        thresholds.append(to_cents(match.group(1)))
        return " "

    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
        rest = ASK_OVER.sub(grab, sentence)

        job_caps += [to_cents(a) for a in PER_JOB.findall(rest)]
        day_caps += [to_cents(a) for a in PER_DAY.findall(rest)]

        if (
            ASK_WORD.search(sentence)
            and SELLER_WORD.search(sentence)
            and NEW_SELLER.search(sentence)
            and not NEVER_ASK.search(sentence)
        ):
            ask_new_sellers = True

        for word, suffix in ONLY.findall(sentence):
            add_unique(allowed, resolve_category(word, bool(suffix)))
        for word, suffix in NEVER_CATEGORY.findall(sentence):
            add_unique(blocked, resolve_category(word, bool(suffix)))

    if not job_caps:
        raise OathParseError(
            "Your oath needs a limit for each job, for example: Spend up to $50 per job."
        )
    if not day_caps:
        raise OathParseError(
            "Your oath needs a limit for each day, for example: Spend at most $100 per day."
        )

    per_job = min(job_caps)
    daily = min(day_caps)
    if per_job <= 0 or daily <= 0:
        raise OathParseError("Your spending limits must be above $0.")

    ask_threshold = min(min(thresholds) if thresholds else per_job, per_job)

    return Policy(
        per_job_cap_cents=per_job,
        daily_cap_cents=daily,
        ask_threshold_cents=ask_threshold,
        allowed_categories=allowed,
        blocked_categories=blocked,
        ask_for_new_sellers=ask_new_sellers,
    )