"""Intent-based routing for the orchestrator (task 4.1.7).

Maps ClaimIntent values to IntentRoute dispatch targets.  Pure logic — no side
effects; the Orchestrator.dispatch_on_intent method wraps this with audit.
"""
from __future__ import annotations

from enum import Enum

from agent_system.parser.schemas.intake import ClaimIntent


class IntentRoute(str, Enum):
    claim_filing = "claim_filing"
    faq_response = "faq_response"
    inquiry = "inquiry"
    complaint_capture = "complaint_capture"


_INTENT_ROUTES: dict[ClaimIntent, IntentRoute] = {
    ClaimIntent.new_claim:        IntentRoute.claim_filing,
    ClaimIntent.faq:              IntentRoute.faq_response,
    ClaimIntent.claim_status:     IntentRoute.inquiry,
    ClaimIntent.policy_question:  IntentRoute.inquiry,
    ClaimIntent.complaint:        IntentRoute.complaint_capture,
}


def dispatch_intent(intent: ClaimIntent) -> IntentRoute:
    """Return the IntentRoute for *intent*.

    Raises KeyError if *intent* has no mapping (guards against future enum values
    added without a corresponding route).
    """
    return _INTENT_ROUTES[intent]
