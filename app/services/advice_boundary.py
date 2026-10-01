"""Keep the tutor on the education side of the line between teaching and advising.

The tutor explains how money works. It must not tell a learner what to buy, sell or
choose, or name a product for them: that is a personal recommendation, which in the UK
is regulated financial advice. The prompt says so, but a prompt is a request, not a
guarantee, so this module adds checks in code:

- `asks_for_recommendation` spots a message that is asking for one. The tutor is then
  told, right beside the question, to explain how to weigh the choice instead, and its
  reply is checked before the learner sees it.
- `reads_like_a_recommendation` and `names_a_product` are the checks on a reply.

These are pattern matches. They are cautious rather than clever: a message wrongly
treated as asking for advice still gets a useful, general answer.
"""
import re

_PRODUCT = (
    r"(?:funds?|stocks?|shares?|etfs?|isas?|sipps?|pensions?|providers?|platforms?|brokers?|banks?|"
    r"accounts?|(?:credit )?cards?|crypto\w*|coins?|investments?|mortgages?|loans?|bonds?|trusts?|apps?)"
)
_MONEY = r"(?:my|the|some|all|any|more|it|that|this|money|cash|savings|everything|£?\d)"
_ACTION = (
    rf"(?:buy|sell|invest|put {_MONEY}|move {_MONEY}|open|choose|pick|go (?:with|for)|switch|transfer|cash in|"
    rf"withdraw|pay off|overpay|take out|remortgage|consolidate)"
)

# Asking how something works ("how do I open an ISA?", "which ISAs count towards the allowance?")
# is not asking for a recommendation, so these look for "should I", "best" and similar.
_ASKS = [
    re.compile(rf"\b(?:should|shall|ought|must)\s+(?:i|we)\b.{{0,80}}\b{_ACTION}\b", re.IGNORECASE),
    re.compile(rf"\b(?:is|would) it (?:be )?(?:better|best|wise|sensible|smart|worth)\b.{{0,60}}\b{_ACTION}\b", re.IGNORECASE),
    re.compile(r"\b(?:what|where|which)\s+should\s+(?:i|we)\b", re.IGNORECASE),
    re.compile(
        rf"\bwhich\b.{{0,60}}\b{_PRODUCT}\b.{{0,60}}\b(?:should|best|better|right for|good for|to (?:buy|choose|pick|get|open|use|go))\b",
        re.IGNORECASE,
    ),
    re.compile(rf"\bwhich\b.{{0,40}}\b(?:is|are) (?:the )?(?:best|better|safest)\b", re.IGNORECASE),
    re.compile(rf"\b(?:best|top|safest)\b.{{0,40}}\b{_PRODUCT}\b", re.IGNORECASE),
    re.compile(r"\b(?:recommend|suggest|advise)\b", re.IGNORECASE),
    re.compile(r"\b(?:is|are|was)\b.{0,60}\b(?:a good|a bad|a safe|a wise|worth)\b.{0,30}\b(?:invest\w*|buy\w*|bet)\b", re.IGNORECASE),
    re.compile(r"\bworth (?:buying|investing)\b", re.IGNORECASE),
    re.compile(r"\b(?:tell|advise) me (?:what|which|where|whether)\b", re.IGNORECASE),
    re.compile(r"\bwhat would you (?:do|buy|choose|pick|invest)\b", re.IGNORECASE),
    re.compile(r"\bgood time to (?:buy|sell|invest)\b", re.IGNORECASE),
]

_RECOMMENDS = [
    re.compile(
        r"\bI(?:'d| would)?\s+(?:strongly |highly |personally |definitely )?(?:recommend|suggest|advise)\s+"
        r"(?:that you |you |to )?(?:buy|sell|invest|put|open|choos|go|pick|switch|mov|tak|get|us|start|stick|consider)\w*",
        re.IGNORECASE,
    ),
    re.compile(
        r"\byou should\s+(?:definitely |probably |really |just |simply |also )?"
        r"(?:buy|sell|invest in|put (?:your|the|that|all|some)|go (?:with|for)|pick|choose|switch to|"
        r"move (?:your|the|that)|open an?|take out|cash in)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:my|our) (?:recommendation|advice|suggestion|pick|top pick) (?:is|would be)\b", re.IGNORECASE),
    re.compile(rf"\bthe best\s+(?:\w+\s+){{0,3}}?(?:option|choice|{_PRODUCT})\s+(?:for you\s+)?(?:is|would be)\b", re.IGNORECASE),
    re.compile(r"\b(?:definitely|just|simply) (?:buy|sell|invest in|go (?:with|for))\b", re.IGNORECASE),
    re.compile(r"\bif I were you\b", re.IGNORECASE),
    re.compile(
        r"\b(?:consider|try|start by|think about)\s+(?:opening|buying|selling|investing|switching|moving|transferring|taking out)\b",
        re.IGNORECASE,
    ),
]

# Well-known names of platforms, banks, fund houses, companies and coins. Not exhaustive: it is a
# backstop for the commonest ways a model names a product. Matched with their capitals, so the fruit
# and the river do not count. Indexes such as the FTSE 100 are concepts, not products, and are absent.
_KNOWN_NAMES = (
    "Vanguard", "Hargreaves Lansdown", "AJ Bell", "Fidelity", "Nutmeg", "Moneybox", "Freetrade",
    "Trading 212", "eToro", "Interactive Investor", "Wealthify", "Moneyfarm", "InvestEngine",
    "BlackRock", "iShares", "Legal & General", "Aviva", "Scottish Widows", "Standard Life",
    "Monzo", "Starling", "Revolut", "Nationwide", "Barclays", "HSBC", "Lloyds", "NatWest", "Santander",
    "Halifax", "Marcus", "Bitcoin", "Ethereum", "Dogecoin", "Solana", "Binance", "Coinbase",
    "Tesla", "Nvidia", "Apple", "Amazon", "Microsoft", "Alphabet", "Google", "Meta",
)
_NAME = re.compile(r"(?<![\w-])(?:" + "|".join(re.escape(name) for name in _KNOWN_NAMES) + r")(?![\w-])")

BOUNDARY_INSTRUCTION = (
    "[This asks for a personal recommendation, which you must not give. Do not recommend, rank or name any "
    "specific product, fund, share, coin, company, provider or account, and do not tell me what to do with my "
    "money. Instead: say in one sentence that you cannot recommend what to choose, then explain in three or "
    "four short sentences what someone should weigh up when making this kind of choice (such as cost, risk, "
    "how long the money can be left, and how quickly it can be reached), and offer one thing I could learn next.]"
)

BOUNDARY_FALLBACK = (
    "I can't recommend what to buy, sell or choose. I teach how money works, and the right choice depends on "
    "your own circumstances.\n"
    "For a decision like this, it helps to compare four things about each option: what it costs you (fees, "
    "charges or interest), what could go wrong, when you will need the money, and how quickly you could get "
    "at it. Ask me about any of those and I'll explain it.\n"
    "For a personal recommendation, a regulated financial adviser can give one; MoneyHelper explains how to find one."
)

ADVICE_NOTE = (
    "Reminder: the tutor explains how things work. It cannot recommend what you personally should buy, sell "
    "or do with your money, so treat anything above that reads that way as a general example."
)


def asks_for_recommendation(message: str) -> bool:
    """True when a learner's message is asking what they should buy, choose or do."""

    return any(pattern.search(message) for pattern in _ASKS)


def reads_like_a_recommendation(reply: str) -> bool:
    """True when a reply tells the learner what to buy, sell or choose."""

    return any(pattern.search(reply) for pattern in _RECOMMENDS)


def names_a_product(reply: str, message: str) -> bool:
    """True when a reply brings up a well-known product or company name the learner did not mention."""

    said = message.lower()  # learners rarely type the capitals
    return any(name.lower() not in said for name in _NAME.findall(reply))
