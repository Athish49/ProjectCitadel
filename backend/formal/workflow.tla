---------------------------- MODULE workflow ----------------------------
\* Formal specification of the SecureClaim claim-workflow state machine.
\* Derived from agent_system/orchestrator/transitions.py — _VALID_EDGES and
\* _check_guard().  Sprint 5.2.1.
\*
\* Primary model checker: formal/check_spec.py (Python BFS — no TLC installation required).
\* To run TLC directly: java -jar tla2tools.jar -config formal/workflow.cfg formal/workflow.tla
\*
\* Checked properties:
\*   INVARIANT : TypeOK
\*   PROPERTY  : ClosedIsAbsorbing, ForwardProgress
\*   PROPERTY  : EventualClosure  (requires WF_vars in Spec)

EXTENDS Naturals, FiniteSets

\* ---------------------------------------------------------------------------
\* Value domains
\* ---------------------------------------------------------------------------

Stages == {
    "INTAKE",
    "IDENTITY_PENDING",
    "IDENTITY_VERIFIED",
    "PROCESSING",
    "DECIDED",
    "SETTLED",
    "ESCALATED",
    "DENIED",
    "CLOSED"
}

FraudDecisions == {"NONE", "CLEAR", "FLAG", "DENY"}

\* Finite amount domain required for TLC exhaustive exploration.
\* 0 = unset; 10000 = at the auto-approval limit; 15000 = over-limit.
AmountDomain == {0, 10000, 15000}

AUTO_APPROVE_LIMIT == 10000

\* Topological rank used to state the ForwardProgress property.
\* SETTLED / ESCALATED / DENIED share rank 5 — they are co-terminal siblings.
Rank(s) ==
    CASE s = "INTAKE"            -> 0
      [] s = "IDENTITY_PENDING"  -> 1
      [] s = "IDENTITY_VERIFIED" -> 2
      [] s = "PROCESSING"        -> 3
      [] s = "DECIDED"           -> 4
      [] s = "SETTLED"           -> 5
      [] s = "ESCALATED"         -> 5
      [] s = "DENIED"            -> 5
      [] s = "CLOSED"            -> 6

\* ---------------------------------------------------------------------------
\* State variables
\* ---------------------------------------------------------------------------

VARIABLES
    stage,               \* current ClaimStage (string drawn from Stages)
    intake_complete,     \* intake form submitted — unlocks INTAKE→IDENTITY_PENDING
    identity_verified,   \* identity check passed — unlocks PENDING→VERIFIED
    damage_assessed,     \* damage report ready — part of PROCESSING→DECIDED guard
    coverage_calculated, \* coverage figure ready — part of PROCESSING→DECIDED guard
    complaint_captured,  \* complaint on file — unlocks VERIFIED→ESCALATED
    fraud_decision,      \* scoring result: "NONE" until set, then "CLEAR"|"FLAG"|"DENY"
    settlement_amount    \* proposed payout; 0 = not yet proposed

vars == <<
    stage,
    intake_complete,
    identity_verified,
    damage_assessed,
    coverage_calculated,
    complaint_captured,
    fraud_decision,
    settlement_amount
>>

\* ---------------------------------------------------------------------------
\* Type invariant  (checked as INVARIANT in TLC)
\* ---------------------------------------------------------------------------

TypeOK ==
    /\ stage               \in Stages
    /\ intake_complete     \in BOOLEAN
    /\ identity_verified   \in BOOLEAN
    /\ damage_assessed     \in BOOLEAN
    /\ coverage_calculated \in BOOLEAN
    /\ complaint_captured  \in BOOLEAN
    /\ fraud_decision      \in FraudDecisions
    /\ settlement_amount   \in AmountDomain

\* ---------------------------------------------------------------------------
\* Initial state
\* ---------------------------------------------------------------------------

Init ==
    /\ stage               = "INTAKE"
    /\ intake_complete     = FALSE
    /\ identity_verified   = FALSE
    /\ damage_assessed     = FALSE
    /\ coverage_calculated = FALSE
    /\ complaint_captured  = FALSE
    /\ fraud_decision      = "NONE"
    /\ settlement_amount   = 0

\* ---------------------------------------------------------------------------
\* Workflow transitions
\* 11 actions — one per edge in _VALID_EDGES, each guarded by _check_guard()
\* ---------------------------------------------------------------------------

\* INTAKE → IDENTITY_PENDING
\* _check_guard: intake_complete must be True
IntakeToPending ==
    /\ stage = "INTAKE"
    /\ intake_complete = TRUE
    /\ stage' = "IDENTITY_PENDING"
    /\ UNCHANGED <<intake_complete, identity_verified, damage_assessed,
                   coverage_calculated, complaint_captured,
                   fraud_decision, settlement_amount>>

\* IDENTITY_PENDING → IDENTITY_VERIFIED
\* _check_guard: identity_verified must be True
PendingToVerified ==
    /\ stage = "IDENTITY_PENDING"
    /\ identity_verified = TRUE
    /\ stage' = "IDENTITY_VERIFIED"
    /\ UNCHANGED <<intake_complete, identity_verified, damage_assessed,
                   coverage_calculated, complaint_captured,
                   fraud_decision, settlement_amount>>

\* IDENTITY_VERIFIED → PROCESSING  (orchestrator-initiated; no data guard)
VerifiedToProcessing ==
    /\ stage = "IDENTITY_VERIFIED"
    /\ stage' = "PROCESSING"
    /\ UNCHANGED <<intake_complete, identity_verified, damage_assessed,
                   coverage_calculated, complaint_captured,
                   fraud_decision, settlement_amount>>

\* IDENTITY_VERIFIED → ESCALATED  (complaint path — task 4.1.9)
\* _check_guard: complaint_captured must be True
VerifiedToEscalated ==
    /\ stage = "IDENTITY_VERIFIED"
    /\ complaint_captured = TRUE
    /\ stage' = "ESCALATED"
    /\ UNCHANGED <<intake_complete, identity_verified, damage_assessed,
                   coverage_calculated, complaint_captured,
                   fraud_decision, settlement_amount>>

\* PROCESSING → DECIDED
\* _check_guard: all three work products must be present
ProcessingToDecided ==
    /\ stage = "PROCESSING"
    /\ damage_assessed     = TRUE
    /\ coverage_calculated = TRUE
    /\ fraud_decision /= "NONE"
    /\ stage' = "DECIDED"
    /\ UNCHANGED <<intake_complete, identity_verified, damage_assessed,
                   coverage_calculated, complaint_captured,
                   fraud_decision, settlement_amount>>

\* DECIDED → SETTLED
\* _check_guard: fraud clear AND proposed amount within auto-approval limit
DecidedToSettled ==
    /\ stage = "DECIDED"
    /\ fraud_decision = "CLEAR"
    /\ settlement_amount > 0
    /\ settlement_amount <= AUTO_APPROVE_LIMIT
    /\ stage' = "SETTLED"
    /\ UNCHANGED <<intake_complete, identity_verified, damage_assessed,
                   coverage_calculated, complaint_captured,
                   fraud_decision, settlement_amount>>

\* DECIDED → ESCALATED
\* _check_guard: flagged/denied fraud OR amount exceeds auto-approval limit
DecidedToEscalated ==
    /\ stage = "DECIDED"
    /\ \/ fraud_decision \in {"FLAG", "DENY"}
       \/ settlement_amount > AUTO_APPROVE_LIMIT
    /\ stage' = "ESCALATED"
    /\ UNCHANGED <<intake_complete, identity_verified, damage_assessed,
                   coverage_calculated, complaint_captured,
                   fraud_decision, settlement_amount>>

\* DECIDED → DENIED  (administrative override — no data guard)
DecidedToDenied ==
    /\ stage = "DECIDED"
    /\ stage' = "DENIED"
    /\ UNCHANGED <<intake_complete, identity_verified, damage_assessed,
                   coverage_calculated, complaint_captured,
                   fraud_decision, settlement_amount>>

\* SETTLED → CLOSED
SettledToClosed ==
    /\ stage = "SETTLED"
    /\ stage' = "CLOSED"
    /\ UNCHANGED <<intake_complete, identity_verified, damage_assessed,
                   coverage_calculated, complaint_captured,
                   fraud_decision, settlement_amount>>

\* ESCALATED → CLOSED
EscalatedToClosed ==
    /\ stage = "ESCALATED"
    /\ stage' = "CLOSED"
    /\ UNCHANGED <<intake_complete, identity_verified, damage_assessed,
                   coverage_calculated, complaint_captured,
                   fraud_decision, settlement_amount>>

\* DENIED → CLOSED
DeniedToClosed ==
    /\ stage = "DENIED"
    /\ stage' = "CLOSED"
    /\ UNCHANGED <<intake_complete, identity_verified, damage_assessed,
                   coverage_calculated, complaint_captured,
                   fraud_decision, settlement_amount>>

\* ---------------------------------------------------------------------------
\* Environment actions
\* Monotonic setters model external actors satisfying guard pre-conditions.
\* Boolean flags may only flip FALSE→TRUE; fraud_decision and settlement_amount
\* may only be set once (from their "unset" sentinel value).
\* ---------------------------------------------------------------------------

SetIntakeComplete ==
    /\ intake_complete = FALSE
    /\ intake_complete' = TRUE
    /\ UNCHANGED <<stage, identity_verified, damage_assessed,
                   coverage_calculated, complaint_captured,
                   fraud_decision, settlement_amount>>

SetIdentityVerified ==
    /\ identity_verified = FALSE
    /\ identity_verified' = TRUE
    /\ UNCHANGED <<stage, intake_complete, damage_assessed,
                   coverage_calculated, complaint_captured,
                   fraud_decision, settlement_amount>>

SetDamageAssessed ==
    /\ damage_assessed = FALSE
    /\ damage_assessed' = TRUE
    /\ UNCHANGED <<stage, intake_complete, identity_verified,
                   coverage_calculated, complaint_captured,
                   fraud_decision, settlement_amount>>

SetCoverageCalculated ==
    /\ coverage_calculated = FALSE
    /\ coverage_calculated' = TRUE
    /\ UNCHANGED <<stage, intake_complete, identity_verified,
                   damage_assessed, complaint_captured,
                   fraud_decision, settlement_amount>>

SetComplaintCaptured ==
    /\ complaint_captured = FALSE
    /\ complaint_captured' = TRUE
    /\ UNCHANGED <<stage, intake_complete, identity_verified,
                   damage_assessed, coverage_calculated,
                   fraud_decision, settlement_amount>>

\* fraud_decision transitions only out of "NONE"
SetFraudDecision(d) ==
    /\ d \in {"CLEAR", "FLAG", "DENY"}
    /\ fraud_decision = "NONE"
    /\ fraud_decision' = d
    /\ UNCHANGED <<stage, intake_complete, identity_verified,
                   damage_assessed, coverage_calculated,
                   complaint_captured, settlement_amount>>

\* settlement_amount transitions only out of 0 (unset sentinel)
SetSettlementAmount(a) ==
    /\ a \in AmountDomain \ {0}
    /\ settlement_amount = 0
    /\ settlement_amount' = a
    /\ UNCHANGED <<stage, intake_complete, identity_verified,
                   damage_assessed, coverage_calculated,
                   complaint_captured, fraud_decision>>

\* ---------------------------------------------------------------------------
\* Next relation
\* ---------------------------------------------------------------------------

Next ==
    \/ IntakeToPending
    \/ PendingToVerified
    \/ VerifiedToProcessing
    \/ VerifiedToEscalated
    \/ ProcessingToDecided
    \/ DecidedToSettled
    \/ DecidedToEscalated
    \/ DecidedToDenied
    \/ SettledToClosed
    \/ EscalatedToClosed
    \/ DeniedToClosed
    \/ SetIntakeComplete
    \/ SetIdentityVerified
    \/ SetDamageAssessed
    \/ SetCoverageCalculated
    \/ SetComplaintCaptured
    \/ \E d \in {"CLEAR", "FLAG", "DENY"} : SetFraudDecision(d)
    \/ \E a \in AmountDomain \ {0}        : SetSettlementAmount(a)

\* ---------------------------------------------------------------------------
\* Specification
\* Weak fairness ensures progress whenever any Next action stays enabled.
\* ---------------------------------------------------------------------------

Spec == Init /\ [][Next]_vars /\ WF_vars(Next)

\* ---------------------------------------------------------------------------
\* Safety properties  (checked as PROPERTY in TLC — action formulas)
\* ---------------------------------------------------------------------------

\* Once CLOSED the stage never changes (absorbing terminal state).
ClosedIsAbsorbing ==
    [][stage = "CLOSED" => stage' = "CLOSED"]_vars

\* Every stage change strictly increases topological rank; no backward moves.
\* Backward edges enable replay attacks — this invariant guards against them.
ForwardProgress ==
    [][stage /= stage' => Rank(stage') > Rank(stage)]_vars

\* ---------------------------------------------------------------------------
\* Liveness property  (checked as PROPERTY in TLC — temporal formula)
\* ---------------------------------------------------------------------------

\* Under weak fairness every execution eventually closes the claim.
EventualClosure == <>(stage = "CLOSED")

\* ---------------------------------------------------------------------------
\* Write-once integrity properties  (NIST SP 800-53 SI-7 / AU-9, PCI-DSS Req. 6)
\* These formalise the monotonic-setter constraints in successors() of check_spec.py.
\* ---------------------------------------------------------------------------

\* Boolean guard flags are monotonically non-decreasing (FALSE → TRUE only).
\* Prevents replay attacks that reset completed workflow steps.
MonotonicFlags ==
    [][ /\ (intake_complete     => intake_complete')
        /\ (identity_verified   => identity_verified')
        /\ (damage_assessed     => damage_assessed')
        /\ (coverage_calculated => coverage_calculated')
        /\ (complaint_captured  => complaint_captured') ]_vars

\* Once the fraud score is set it is immutable.  Prevents score-laundering.
FraudDecisionFinal ==
    [][fraud_decision /= "NONE" => fraud_decision' = fraud_decision]_vars

\* Once a settlement amount is proposed it is immutable.  Prevents mid-flight tampering.
SettlementAmountFinal ==
    [][settlement_amount /= 0 => settlement_amount' = settlement_amount]_vars

=============================================================================
\* Derived from transitions.py — Sprint 5.2.1
