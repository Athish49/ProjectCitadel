export type RiskStatus = "accepted" | "planned" | "won't-do";

export interface ResidualRisk {
  id: string;
  title: string;
  description: string;
  whyItRemains: string;
  productionMitigation: string;
  status: RiskStatus;
  patternIds: string[];
}

export const RESIDUAL_RISKS: ResidualRisk[] = [
  {
    id: "RR-01",
    title: "OCR false-negatives leave PII in pre-redaction pipeline",
    description:
      "The vision pre-redaction stage uses OCR to detect and redact PII in images before they reach the LLM. Low-contrast text, handwriting, or rotated glyphs can produce OCR misses, silently passing unredacted personal data downstream.",
    whyItRemains:
      "State-of-the-art OCR achieves ~98% recall; the remaining ~2% gap is a fundamental model-accuracy limit. A 100%-accurate redaction stage would require human review, breaking the automated flow.",
    productionMitigation:
      "All images are logged with a content hash. A weekly batch job samples 1% of processed images for human audit. PII leakage rate is tracked as an SLO metric. Per-attachment IFC label PERSONAL is set conservatively at ingest.",
    status: "accepted",
    patternIds: ["P6"],
  },
  {
    id: "RR-02",
    title: "Jailbroken parser LLM can emit schema-valid adversarial JSON",
    description:
      "The Dual-LLM pattern uses a restricted parser model to produce structured JSON from untrusted claim text. A sufficiently crafted adversarial prompt could coerce the parser into emitting JSON that passes schema validation but carries injected field values (e.g., inflated settlement_amount, fabricated policy_number).",
    whyItRemains:
      "JSON schema validation is structural, not semantic. Detecting semantically out-of-range values requires business-rule validation that is claim-type-specific and not fully enumerable. The parser LLM is a probabilistic function; no formal guarantee of output fidelity exists.",
    productionMitigation:
      "Numeric fields are bounded by claim-type limits in post-schema validation. High-value claims (>$10k) require adjuster review before settlement dispatch. Anomaly detection flags statistical outliers in extracted amounts.",
    status: "accepted",
    patternIds: ["P1"],
  },
  {
    id: "RR-03",
    title: "Inter-agent capability signing operates within a single process",
    description:
      "The Ed25519 capability token implementation signs and verifies tokens within the same Python process. This demonstrates the cryptographic pattern correctly but does not enforce network-level isolation: a compromised process can forge tokens by accessing the in-memory signing key.",
    whyItRemains:
      "This is a portfolio/demonstration system. Running agents as separate network services with HSM-backed key storage is architecturally correct but outside the scope of a single-developer showcase. The signing key is never serialised to disk or exposed via API.",
    productionMitigation:
      "In a production deployment, each agent would run in a separate container with an identity bound to a hardware-backed key (e.g., AWS KMS, GCP Cloud HSM). The current implementation is labelled as a pattern demonstration, not a production security boundary.",
    status: "accepted",
    patternIds: ["P8"],
  },
  {
    id: "RR-04",
    title: "LLM outputs are nondeterministic; red-team statistics are point-in-time",
    description:
      "The Adversary page displays attack success rates computed from the live red-team agent against the current model checkpoint. Anthropic may update the underlying model without notice, changing the attack surface and invalidating displayed statistics.",
    whyItRemains:
      "Hosted model providers (Anthropic, OpenAI) do not expose version-pinning or changelog webhooks for safety-relevant model updates. Caching test results would show stale data; live evaluation is expensive (~$0.02/run).",
    productionMitigation:
      "Statistics are rendered with a 'last evaluated' timestamp. The Adversary page includes a disclaimer that results reflect the model version at evaluation time. Regression tests run on a weekly schedule via CI to detect drift.",
    status: "accepted",
    patternIds: [],
  },
  {
    id: "RR-05",
    title: "No per-customer rate limiting on agent-invocation endpoint",
    description:
      "The claims processing endpoint accepts requests from any authenticated customer without enforcing per-customer request quotas. A single customer could submit thousands of claims in a burst, exhausting the Anthropic API quota shared across all tenants.",
    whyItRemains:
      "Rate limiting requires a shared counter store (Redis or similar) with TTL semantics, which is not provisioned in the current single-host deployment. Implementing it correctly without introducing a new SPOF requires infrastructure work.",
    productionMitigation:
      "Monthly Anthropic spend cap ($50) acts as a hard ceiling. In production, an API gateway (AWS API Gateway, Kong) should enforce per-customer token-bucket limits. This work is tracked and scheduled before public launch.",
    status: "planned",
    patternIds: ["P11"],
  },
  {
    id: "RR-06",
    title: "RLS policies fail open when app.current_customer_id is not set",
    description:
      "PostgreSQL Row-Level Security is enforced via `current_setting('app.current_customer_id', true)`. If a database connection is reused from a connection pool without setting this parameter, the RLS predicate evaluates to NULL, which PostgreSQL treats as FALSE — rows are invisible but not errored. A misconfigured application layer could silently see no rows rather than a security error.",
    whyItRemains:
      "PostgreSQL does not provide a built-in mechanism to enforce that a session variable is set before a query runs. The fail-silent-rather-than-fail-error behaviour is a PostgreSQL design property. A trigger-based guard adds latency on every SELECT.",
    productionMitigation:
      "All database access goes through a single `get_db_session()` factory that sets `app.current_customer_id` before yielding. Integration tests assert that a bare connection with no variable set returns empty result sets. Monitoring alerts on empty-result anomalies.",
    status: "accepted",
    patternIds: ["P7"],
  },
  {
    id: "RR-07",
    title: "LSB steganography detection fails on JPEG-recompressed images",
    description:
      "The steganography detector uses a chi-square test on LSB distributions to flag images with hidden payloads. JPEG is a lossy format; re-saving any image as JPEG destroys LSB patterns, making steganographic content invisible to this detector.",
    whyItRemains:
      "Lossless re-encoding of all uploaded images would change file hashes, break document provenance tracking, and add compute cost. Detecting steganography in JPEG requires frequency-domain analysis (DCT coefficient statistics) which has a high false-positive rate on natural images.",
    productionMitigation:
      "The detector is applied to PNG, TIFF, and BMP uploads where LSB analysis is reliable. JPEG uploads are flagged with a lower-confidence label and routed to adjuster review for high-value claims. This limitation is documented in the operator runbook.",
    status: "accepted",
    patternIds: ["P6"],
  },
  {
    id: "RR-08",
    title: "Training-data and model-weight attacks are out of scope",
    description:
      "Attacks that target model training pipelines (data poisoning, backdoor implantation) or model weights directly (#48–#57 in the attack matrix) are not mitigated by any control in this system.",
    whyItRemains:
      "This system uses hosted foundation models (Claude via Anthropic API). The training pipeline and model weights are entirely outside the operator's control surface. Mitigating these attacks would require training or fine-tuning proprietary models, which is out of scope for this project.",
    productionMitigation:
      "Anthropic's usage policies and security practices are relied upon for training-pipeline integrity. The system uses model cards and Anthropic's published safety evaluations as assurance evidence. Supply-chain attestation (model provenance) is not independently verifiable.",
    status: "won't-do",
    patternIds: [],
  },
  {
    id: "RR-09",
    title: "Prompt extraction via paraphrasing evades egress content filter",
    description:
      "The egress filter (P12) inspects LLM responses for verbatim repetition of system-prompt content. An adversarial user can instruct the model to paraphrase or restate the system prompt semantically, producing output that carries the same information without triggering pattern-match rules.",
    whyItRemains:
      "Semantic similarity detection at inference time requires embedding-based comparison against a secret corpus, which is computationally expensive and introduces a latency SLA risk. The filter is intentionally heuristic-first.",
    productionMitigation:
      "System prompts are classified CONFIDENTIAL in the IFC lattice and never logged in raw form. The egress filter catches high-confidence verbatim leaks. Adjuster training includes instructions not to ask the agent to repeat or describe its instructions. Novel paraphrase attacks are a known open problem in adversarial ML.",
    status: "accepted",
    patternIds: ["P12"],
  },
  {
    id: "RR-10",
    title: "IFC labelling errors at data-entry boundaries are undetectable at runtime",
    description:
      "The IFC lattice enforces non-interference once labels are assigned. If a data-entry point (API handler, file ingest) assigns the wrong label — e.g., labelling CONFIDENTIAL data as PERSONAL — the enforcement engine has no ground truth to detect the error. Mislabelled data flows freely to sinks that should not receive it.",
    whyItRemains:
      "Label correctness is a policy decision, not an algorithmic one. Automated label inference from content (NLP classification) has ~5% error rates and would require continuous model updates as claim formats change. Runtime detection of labelling bugs requires taint-tracking at the field level, which is not implemented.",
    productionMitigation:
      "Labels are assigned by claim-type templates, not per-field heuristics, reducing the per-field error surface. New claim types require a formal data classification review before the template is deployed. Quarterly audits compare assigned labels against a sample of adjuster-reviewed claims.",
    status: "accepted",
    patternIds: ["P3"],
  },
  {
    id: "RR-11",
    title: "Adversarial red-team agent incurs real Anthropic API costs",
    description:
      "The Adversary Console runs a live multi-turn red-team agent against the production claim-processing endpoint. Each run invokes the Anthropic API for both the attacker and defender, at ~$0.02 per full attack sequence. A user triggering repeated runs could consume the monthly budget.",
    whyItRemains:
      "The Adversary page is a demonstration of the red-team capability, not a production security tool. A $50/month hard cap on the Anthropic account prevents runaway spend, but this cap applies to all API usage, not just adversarial runs.",
    productionMitigation:
      "The Adversary page requires no authentication for demo purposes. In production, it would be gated behind an admin role. Rate limiting (RR-05) will add per-user request quotas once implemented. Current spend is monitored in the Anthropic dashboard with a Slack alert at 80% of monthly cap.",
    status: "accepted",
    patternIds: ["P11"],
  },
  {
    id: "RR-12",
    title: "Ed25519 key rotation is manual with no automated revocation",
    description:
      "The capability token signing key is a static Ed25519 key pair generated at startup. There is no key rotation schedule, no revocation list, and no mechanism to invalidate tokens signed with a compromised key without restarting the service.",
    whyItRemains:
      "Automated key rotation requires a key management service (KMS) or a distributed revocation protocol (e.g., OCSP, CRL). Neither is provisioned in the current single-host, demo-scale deployment. Token TTLs (15 minutes) limit the window of exposure for any individual token.",
    productionMitigation:
      "Key rotation is documented as a required operational procedure before production launch. The signing key is stored in environment variables (not source code). In production, AWS KMS or HashiCorp Vault would manage key lifecycle. This is tracked as a pre-launch requirement.",
    status: "planned",
    patternIds: ["P8", "P12"],
  },
  {
    id: "RR-13",
    title: "Container escape via kernel zero-day defeats process-level sandbox",
    description:
      "Tool execution in the agentic pipeline relies on OS-level process isolation (subprocess spawning with restricted permissions). A kernel-level vulnerability exploited by malicious tool output could allow a compromised subprocess to escape the sandbox and access the host file system or network.",
    whyItRemains:
      "Kernel zero-days are, by definition, unmitigated by userspace controls. Defence-in-depth at the kernel level requires hardware virtualisation (VM-level isolation per request), which has prohibitive latency for a synchronous claims API.",
    productionMitigation:
      "Tool execution runs under a dedicated low-privilege OS user with no network access and a restricted filesystem mount. seccomp-bpf filter blocks all syscalls not required by the tool allowlist. Container images are rebuilt weekly with the latest kernel patches. gVisor or Firecracker is evaluated as a pre-launch upgrade path.",
    status: "accepted",
    patternIds: ["P5"],
  },
];
