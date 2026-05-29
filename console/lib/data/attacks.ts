import type { MatrixRow, MatrixClass, AttackCategory, PatternId } from "@/lib/types/showcase";

interface AttackEntry {
  attackId: number;
  name: string;
  description: string;
  patterns: PatternId[];
}

export const ATTACKS: AttackEntry[] = [
  // PROMPT & INPUT MANIPULATION
  { attackId: 1,  name: "Direct Prompt Injection",            description: "Crafted inputs that override system or developer instructions.",                                                                                                          patterns: ["P1"] },
  { attackId: 2,  name: "Indirect Prompt Injection",          description: "Malicious instructions hidden in content the agent retrieves — emails, PDFs, web pages, or documents.",                                                                  patterns: ["P1", "P5"] },
  { attackId: 3,  name: "Cross-Context Injection",            description: "Instructions embedded in one context that influence agent behavior in another.",                                                                                          patterns: ["P1"] },
  { attackId: 4,  name: "Jailbreaking",                       description: "Bypassing AI safety alignments through adversarial prompting.",                                                                                                           patterns: [] },
  { attackId: 5,  name: "Adversarial Examples / Evasion",     description: "Carefully crafted inputs that cause unsafe or incorrect outputs without changing the model itself.",                                                                      patterns: [] },
  { attackId: 6,  name: "Cross-Modal / Multimodal Injection", description: "Injected instructions hidden inside images, audio, PDFs, or documents that bypass text-only filters.",                                                                   patterns: ["P1", "P5", "P6"] },
  { attackId: 7,  name: "Semantic Prompt Injection",          description: "Injections hidden in symbolic or multimodal content that static filters cannot detect.",                                                                                  patterns: ["P1"] },
  { attackId: 8,  name: "Zero-Click Injection",               description: "Attacks like EchoLeak where the user never interacts; the agent is compromised through passive content consumption alone.",                                               patterns: ["P1", "P5"] },

  // GOAL & BEHAVIOR HIJACKING
  { attackId: 9,  name: "Agent Goal Hijack (ASI01)",          description: "Redirecting the agent's decision-making pathways or objectives entirely.",                                                                                                patterns: ["P2", "P12"] },
  { attackId: 10, name: "Semantic Layer Exploitation",        description: "Manipulating the agent's understanding of what it should do rather than its inputs or outputs directly.",                                                                 patterns: [] },
  { attackId: 11, name: "Chain-of-Thought Manipulation",      description: "Corrupting intermediate reasoning steps so the agent arrives at a malicious conclusion through seemingly legitimate logic.",                                               patterns: ["P2"] },
  { attackId: 12, name: "Calendar / Quiet Mode Drift",        description: "Subtle instruction injection that slowly reweights the agent's objectives over time.",                                                                                    patterns: [] },
  { attackId: 13, name: "Goal Misalignment Cascade",          description: "Exploiting misaligned objectives that propagate across multi-agent workflows.",                                                                                           patterns: ["P2"] },
  { attackId: 14, name: "Behavioral Drift",                   description: "Gradual deviation of agent behavior from its intended purpose over time.",                                                                                                patterns: ["P12"] },

  // MEMORY & CONTEXT ATTACKS
  { attackId: 15, name: "Memory Poisoning",                   description: "Corrupting the agent's persistent memory so future decisions are influenced by attacker-controlled content.",                                                             patterns: [] },
  { attackId: 16, name: "Context Poisoning",                  description: "Feeding the agent stale, misleading, or tampered context that shapes its reasoning.",                                                                                     patterns: [] },
  { attackId: 17, name: "RAG Index Poisoning",                description: "Injecting attacker-controlled content into the retrieval corpus so agents retrieve it at query time.",                                                                   patterns: [] },
  { attackId: 18, name: "Log Poisoning",                      description: "Writing malicious content into agent log files that the agent later reads for self-diagnostics, triggering injected behavior.",                                          patterns: ["P9"] },
  { attackId: 19, name: "Semantic State Accumulation",        description: "Planting attacker-controlled text that survives across multiple turns and contexts, shaping future reasoning.",                                                           patterns: [] },

  // DATA EXFILTRATION ATTACKS
  { attackId: 20, name: "Direct Data Exfiltration",           description: "Coercing the agent to retrieve and transmit unauthorized data via prompt injection.",                                                                                    patterns: ["P3", "P7"] },
  { attackId: 21, name: "Indirect Exfiltration via Side Channels", description: "Making the agent summarize, forward, or encode sensitive data through what appears to be a legitimate task.",                                                   patterns: ["P3", "P10"] },
  { attackId: 22, name: "Model Inversion Attacks",            description: "Extracting sensitive training data through repeated inference API queries.",                                                                                               patterns: [] },
  { attackId: 23, name: "Membership Inference Attacks",       description: "Determining whether specific records were included in training data.",                                                                                                    patterns: [] },
  { attackId: 24, name: "Indirect Exfiltration via RAG",      description: "Using the model as an unwitting data relay by embedding exfiltration instructions in content it retrieves.",                                                             patterns: ["P3"] },
  { attackId: 25, name: "URL-Based Exfiltration",             description: "Agent produces a URL in output that encodes stolen data; fetching that URL sends the data to the attacker.",                                                              patterns: ["P10"] },
  { attackId: 26, name: "Steganographic Exfiltration",        description: "Encoding and leaking data through hidden signals inside benign-looking outputs or agent-to-agent messages.",                                                              patterns: ["P3", "P10"] },
  { attackId: 27, name: "Side-Channel Summarization Exfiltration", description: "Tricking agents into summarizing private conversations or documents and forwarding them externally (as in the Slack AI incident).",                             patterns: ["P3"] },
  { attackId: 28, name: "Semantic-Layer Data Exfiltration",   description: "Phrasing data retrieval requests as legitimate business tasks so the agent sees them as reasonable (e.g., exporting all records matching pattern X).",                  patterns: ["P3", "P7"] },

  // TOOL & EXECUTION ATTACKS
  { attackId: 29, name: "Tool Misuse & Exploitation (ASI02)", description: "Inducing the agent to misuse legitimate tools for exfiltration, destruction, or workflow hijacking.",                                                                    patterns: ["P4"] },
  { attackId: 30, name: "Unexpected Code Execution / RCE",   description: "Agent generates, modifies, or runs code or commands in unauthorized ways.",                                                                                               patterns: ["P5"] },
  { attackId: 31, name: "Recursive Tool Calls",               description: "Agents invoke tools in loops causing resource exhaustion or unintended behavior.",                                                                                        patterns: ["P11"] },
  { attackId: 32, name: "Unsafe Tool Composition",            description: "Chaining tools in dangerous sequences to achieve outcomes no single tool would allow.",                                                                                   patterns: ["P4"] },
  { attackId: 33, name: "Cross-Tool State Leakage",           description: "Information flowing across tool boundaries in unauthorized ways.",                                                                                                        patterns: ["P4"] },
  { attackId: 34, name: "Tool Budget Exhaustion",             description: "Overwhelming systems with excessive tool invocations (Denial of Wallet).",                                                                                                patterns: ["P11"] },
  { attackId: 35, name: "MCP Tool Poisoning",                 description: "Injecting malicious behavior into Model Context Protocol tools that agents use.",                                                                                         patterns: ["P5"] },
  { attackId: 36, name: "Publish Poisoned AI Agent Tool",     description: "Distributing a compromised tool into agent tool registries (MITRE ATLAS AML technique).",                                                                                patterns: [] },
  { attackId: 37, name: "SQL Injection via Agent",            description: "Agents with database access being coerced into running unauthorized SQL queries.",                                                                                        patterns: ["P7"] },

  // IDENTITY, PRIVILEGE & TRUST ATTACKS
  { attackId: 38, name: "Identity & Privilege Abuse (ASI03)", description: "Exploiting delegation chains, inherited credentials, and weak attribution to escalate privileges.",                                                                       patterns: ["P4"] },
  { attackId: 39, name: "Confused Deputy Attack",             description: "Tricking the agent into using its own permissions on behalf of an attacker.",                                                                                             patterns: ["P4"] },
  { attackId: 40, name: "Agent Impersonation / Spoofing",     description: "One agent or actor pretending to be another to gain trust or redirect actions.",                                                                                          patterns: ["P8"] },
  { attackId: 41, name: "Credential / Token Compromise",      description: "Stealing or forging the agent's API keys, OAuth tokens, or session credentials.",                                                                                        patterns: [] },
  { attackId: 42, name: "Session Hijacking",                  description: "Exploiting built-in trust in Agent-to-Agent (A2A) protocols to hold multi-turn malicious conversations.",                                                                patterns: [] },
  { attackId: 43, name: "Privilege Escalation via Orchestrator Compromise", description: "Compromising the orchestrator agent to gain control of all downstream agents' permissions.",                                                          patterns: ["P2"] },

  // MULTI-AGENT & ORCHESTRATION ATTACKS
  { attackId: 44, name: "Insecure Inter-Agent Communication", description: "Exploiting weaknesses in agent-to-agent protocols, discovery, and validation.",                                                                                          patterns: ["P8"] },
  { attackId: 45, name: "Rogue Agent Injection (ASI10)",      description: "Introducing a malicious or compromised agent into a trusted multi-agent workflow.",                                                                                       patterns: [] },
  { attackId: 46, name: "Orchestration Layer Exploitation",   description: "Compromising the central orchestrator to manipulate the entire workflow without touching individual agents.",                                                             patterns: ["P2"] },
  { attackId: 47, name: "Spoofed Inter-Agent Messages",       description: "Fabricating messages between agents to misdirect entire clusters of autonomous systems.",                                                                                 patterns: ["P8"] },
  { attackId: 48, name: "Malicious Agent Collusion",          description: "Two or more agents coordinating to perform actions neither could accomplish alone.",                                                                                      patterns: [] },
  { attackId: 49, name: "Steganographic Agent Collusion",     description: "Agents exchanging hidden signals through benign-looking messages to coordinate covertly without triggering monitoring.",                                                  patterns: [] },

  // SUPPLY CHAIN & ECOSYSTEM ATTACKS
  { attackId: 50, name: "Agentic Supply Chain Vulnerabilities (ASI04)", description: "Compromising tools, prompts, agents, models, or registries at build-time or runtime.",                                                                    patterns: [] },
  { attackId: 51, name: "ML Supply Chain Compromise",         description: "Inserting malicious components into the ML pipeline — model weights, training data, or libraries.",                                                                      patterns: [] },
  { attackId: 52, name: "Package Hallucination Attack",       description: "Registering malicious packages with names LLMs frequently hallucinate, turning a model weakness into a reliable code injection vector.",                                 patterns: [] },
  { attackId: 53, name: "Poisoned AI Agent Tool",             description: "Pushing a trojanized tool into the agent ecosystem's marketplace or registry.",                                                                                           patterns: [] },
  { attackId: 54, name: "Repository-Controlled Config Exploitation", description: "Malicious configuration files in repositories that silently execute shell commands at project load time.",                                                     patterns: [] },
  { attackId: 55, name: "Skill / Plugin Supply Chain Attack", description: "Compromising third-party plugins or skills that agents install and execute.",                                                                                             patterns: [] },

  // TRAINING & MODEL-LEVEL ATTACKS
  { attackId: 56, name: "Data Poisoning",                     description: "Corrupting a subset of training data to embed malicious behaviors into the model at the source.",                                                                        patterns: [] },
  { attackId: 57, name: "Model Backdoor / Trojan",            description: "Embedding hidden behaviors in the model that activate under specific trigger conditions.",                                                                                patterns: ["P12"] },
  { attackId: 58, name: "Model Extraction / Stealing",        description: "Reproducing a model's capabilities through repeated API queries without access to weights.",                                                                              patterns: [] },
  { attackId: 59, name: "Adversarial Fine-Tuning",            description: "Manipulating the fine-tuning process to bias model behavior toward attacker-desired outcomes.",                                                                           patterns: [] },
  { attackId: 60, name: "Training Pipeline Compromise",       description: "Attacking the data ingestion, labeling, or training infrastructure itself.",                                                                                              patterns: [] },

  // CASCADING & SYSTEMIC FAILURES
  { attackId: 61, name: "Cascading Failures (ASI08)",         description: "A single fault propagating across interconnected agents and workflows, amplifying the impact.",                                                                           patterns: ["P2"] },
  { attackId: 62, name: "Hallucination Propagation",          description: "One agent's hallucinated output being consumed as fact by downstream agents, leading to compounding errors and real-world consequences.",                                 patterns: ["P2"] },
  { attackId: 63, name: "Cross-Zone Causality Chain Attacks", description: "Multi-step attack chains (Input → Retrieval bias → Goal shift → Tool invocation → Exfiltration) treated by defenders as separate events but executed as one chain.",    patterns: ["P2"] },
  { attackId: 64, name: "Goal Misalignment Cascade",          description: "Misaligned goals in one agent spreading across a network of dependent agents.",                                                                                           patterns: ["P2"] },

  // HUMAN-AGENT TRUST EXPLOITATION
  { attackId: 65, name: "Human-Agent Trust Exploitation (ASI09)", description: "Weaponizing anthropomorphism and authority bias to manipulate human oversight.",                                                                                 patterns: [] },
  { attackId: 66, name: "Social Engineering via Agent",       description: "Using the agent's trusted position with users to extract information or permissions.",                                                                                    patterns: ["P10"] },
  { attackId: 67, name: "Authority Spoofing",                 description: "Impersonating a trusted entity (manager, system, service) through the agent interface.",                                                                                  patterns: [] },

  // INFRASTRUCTURE & RUNTIME ATTACKS
  { attackId: 68, name: "Sandbox Escape / Escape to Host",    description: "Agent breaking out of its execution sandbox to access the underlying host system.",                                                                                       patterns: ["P5"] },
  { attackId: 69, name: "Denial of Wallet (DoW)",             description: "Generating excessive API costs or resource consumption to financially harm the operator.",                                                                                patterns: ["P11"] },
  { attackId: 70, name: "Denial of Service via Recursive Loops", description: "Causing agent resource exhaustion through looping behaviors.",                                                                                                     patterns: ["P11"] },
  { attackId: 71, name: "WebSocket Hijacking",                description: "Exploiting unauthenticated local WebSocket connections to silently hijack agent instances (e.g., ClawJacked, CVE-2026-28363).",                                           patterns: [] },
  { attackId: 72, name: "Self-Replicating Agent Worm",        description: "Agents that autonomously spread compromise to other systems or packages (e.g., Shai-Hulud npm worm).",                                                                    patterns: [] },

  // AI AS AN OFFENSIVE WEAPON
  { attackId: 73, name: "AI-Orchestrated Cyberattack",        description: "Using agentic AI to autonomously execute the full cyberattack lifecycle — reconnaissance, exploitation, and exfiltration — against external targets.",                   patterns: [] },
  { attackId: 74, name: "Autonomous Ransomware Execution",    description: "Agents completing the full ransomware lifecycle (encryption, exfiltration, negotiation) autonomously in minutes.",                                                        patterns: [] },
  { attackId: 75, name: "Accelerated Exfiltration",           description: "AI agents compressing what previously took days of manual attacker work into minutes or hours.",                                                                          patterns: [] },

  // PRIVACY & INFERENCE ATTACKS
  { attackId: 76, name: "Model Inversion",                    description: "Reconstructing training data from model outputs.",                                                                                                                         patterns: [] },
  { attackId: 77, name: "Membership Inference",               description: "Determining if a specific individual's data was in the training set.",                                                                                                    patterns: [] },
  { attackId: 78, name: "Prompt Extraction",                  description: "Recovering the system prompt or confidential instructions through adversarial queries.",                                                                                  patterns: ["P10"] },
  { attackId: 79, name: "Training Data Extraction",           description: "Causing the model to regurgitate verbatim training data including PII, credentials, or proprietary content.",                                                             patterns: [] },
];

// ── Category & class metadata ─────────────────────────────────────────────────

export function getAttackCategory(id: number): AttackCategory {
  if (id <= 8)  return "Prompt/Input";
  if (id <= 14) return "Goal Hijack";
  if (id <= 19) return "Memory";
  if (id <= 28) return "Exfiltration";
  if (id <= 37) return "Tool";
  if (id <= 43) return "Identity";
  if (id <= 49) return "Multi-Agent";
  if (id <= 55) return "Supply Chain";
  if (id <= 60) return "Training";
  if (id <= 64) return "Cascading";
  if (id <= 67) return "Trust";
  if (id <= 72) return "Infra";
  if (id <= 75) return "Weapon";
  return "Privacy";
}

// Architecturally not applicable — design eliminates the threat vector.
const ARCHITECTURAL_IDS = new Set([43, 45, 46]);

// Out-of-scope categories (application-layer defences can't address these).
const OOS_CATEGORIES = new Set<AttackCategory>([
  "Supply Chain", "Training", "Weapon", "Privacy",
]);

export function getAttackClass(id: number, patterns: PatternId[]): MatrixClass {
  if (ARCHITECTURAL_IDS.has(id)) return "ARCHITECTURAL";
  if (OOS_CATEGORIES.has(getAttackCategory(id))) return "OUT-OF-SCOPE";
  if (patterns.length > 0) return "LIVE";
  return "OUT-OF-SCOPE";
}

// ── Realistic variant counts for LIVE attacks ─────────────────────────────────

// Pre-set numbers for attacks that appear in the playground or spec examples.
const PRESET: Record<number, { v: number; b: number; p: number; fp: number; minsAgo: number }> = {
   1: { v: 153, b: 153, p:  0, fp: 2, minsAgo:   14 },
   2: { v:  92, b:  91, p:  1, fp: 0, minsAgo:  120 },
   6: { v:  47, b:  47, p:  0, fp: 1, minsAgo:  180 },
   7: { v:  38, b:  38, p:  0, fp: 0, minsAgo:  300 },
   9: { v:  61, b:  60, p:  1, fp: 1, minsAgo:   40 },
  20: { v:  67, b:  65, p:  2, fp: 1, minsAgo:   60 },
  21: { v:  44, b:  44, p:  0, fp: 0, minsAgo:  240 },
  25: { v:  31, b:  31, p:  0, fp: 0, minsAgo:  135 },
  28: { v:  55, b:  54, p:  1, fp: 0, minsAgo:  360 },
  29: { v:  83, b:  82, p:  1, fp: 1, minsAgo:   55 },
  66: { v:  29, b:  28, p:  1, fp: 0, minsAgo:  480 },
  78: { v:  41, b:  41, p:  0, fp: 0, minsAgo:  185 },
};

function lcg(n: number): number {
  return ((n * 1664525 + 1013904223) >>> 0) % 1000;
}

function computeLiveStats(id: number) {
  if (PRESET[id]) {
    const { v, b, p, fp, minsAgo } = PRESET[id];
    return {
      variantCount: v,
      blockedCount: b,
      partialCount: p,
      successfulCount: 0,
      falsePositiveCount: fp,
      lastTestedAt: new Date(Date.now() - minsAgo * 60_000).toISOString(),
    };
  }
  const s = lcg(id);
  const variants = 25 + (s % 130);
  const partial  = s % 5 === 0 ? 2 : s % 3 === 0 ? 1 : 0;
  const fp       = s % 7 === 0 ? 2 : s % 4 === 0 ? 1 : 0;
  const minsAgo  = 10 + (s % (48 * 60));
  return {
    variantCount: variants,
    blockedCount: variants - partial,
    partialCount: partial,
    successfulCount: 0,
    falsePositiveCount: fp,
    lastTestedAt: new Date(Date.now() - minsAgo * 60_000).toISOString(),
  };
}

// ── Public API ────────────────────────────────────────────────────────────────

export function toMatrixRow(entry: AttackEntry): MatrixRow {
  const cls = getAttackClass(entry.attackId, entry.patterns);
  const stats =
    cls === "LIVE"
      ? computeLiveStats(entry.attackId)
      : { variantCount: null, blockedCount: 0, partialCount: 0, successfulCount: 0, falsePositiveCount: 0, lastTestedAt: null };

  return {
    attackId: entry.attackId,
    name: entry.name,
    category: getAttackCategory(entry.attackId),
    class: cls,
    patterns: entry.patterns,
    ...stats,
  };
}

export function getAttack(id: number): AttackEntry | undefined {
  return ATTACKS.find((a) => a.attackId === id);
}
