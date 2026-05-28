# Agentic AI Attack Types & Methods — Complete Master List

> Combined from OWASP Agentic AI Top 10, CSA MAESTRO, NIST AI RMF, MITRE ATLAS, and additional research covering gaps not addressed by any single framework.

---

## 🔴 PROMPT & INPUT MANIPULATION

1. **Direct Prompt Injection** — Crafted inputs that override system or developer instructions
2. **Indirect Prompt Injection** — Malicious instructions hidden in content the agent retrieves (emails, PDFs, web pages, documents)
3. **Cross-Context Injection** — Instructions embedded in one context that influence agent behavior in another
4. **Jailbreaking** — Bypassing AI safety alignments through adversarial prompting
5. **Adversarial Examples / Evasion Inputs** — Carefully crafted inputs that cause unsafe or incorrect outputs without changing the model itself
6. **Cross-Modal / Multimodal Injection** — Injected instructions hidden inside images, audio, PDFs, or documents that bypass text-only filters
7. **Semantic Prompt Injection** — Injections hidden in symbolic or multimodal content that static filters cannot detect
8. **Zero-Click Injection** — Attacks like EchoLeak where the user never interacts; the agent is compromised through passive content consumption alone

---

## 🔴 GOAL & BEHAVIOR HIJACKING

9. **Agent Goal Hijack (ASI01)** — Redirecting the agent's decision-making pathways or objectives entirely
10. **Semantic Layer Exploitation** — Manipulating the agent's *understanding* of what it should do rather than its inputs or outputs directly
11. **Chain-of-Thought (CoT) Manipulation** — Corrupting intermediate reasoning steps so the agent arrives at a malicious conclusion through seemingly legitimate logic
12. **Calendar / Quiet Mode Drift** — Subtle instruction injection that slowly reweights the agent's objectives over time
13. **Goal Misalignment Cascade** — Exploiting misaligned objectives that propagate across multi-agent workflows
14. **Behavioral Drift** — Gradual deviation of agent behavior from its intended purpose over time

---

## 🔴 MEMORY & CONTEXT ATTACKS

15. **Memory Poisoning** — Corrupting the agent's persistent memory so future decisions are influenced by attacker-controlled content
16. **Context Poisoning** — Feeding the agent stale, misleading, or tampered context that shapes its reasoning
17. **RAG Index Poisoning** — Injecting attacker-controlled content into the retrieval corpus so agents retrieve it at query time
18. **Log Poisoning** — Writing malicious content into agent log files that the agent later reads for self-diagnostics, triggering injected behavior
19. **Semantic State Accumulation** — Planting attacker-controlled text that survives across multiple turns and contexts, shaping future reasoning

---

## 🔴 DATA EXFILTRATION ATTACKS

20. **Direct Data Exfiltration via Prompt Injection** — Coercing the agent to retrieve and transmit unauthorized data
21. **Indirect Exfiltration via Side Channels** — Making the agent summarize, forward, or encode sensitive data through what appears to be a legitimate task
22. **Model Inversion Attacks** — Extracting sensitive training data through repeated inference API queries
23. **Membership Inference Attacks** — Determining whether specific records were included in training data
24. **Indirect Exfiltration via RAG / Retrieved Content** — Using the model as an unwitting data relay by embedding exfiltration instructions in content it retrieves
25. **URL-Based Exfiltration** — Agent produces a URL in output that encodes stolen data; fetching that URL sends the data to the attacker
26. **Steganographic Exfiltration** — Encoding and leaking data through hidden signals inside benign-looking outputs or agent-to-agent messages
27. **Side-Channel Summarization Exfiltration** — Tricking agents into summarizing private conversations or documents and forwarding them externally (as in the Slack AI incident)
28. **Semantic-Layer Data Exfiltration** — Phrasing data retrieval requests as legitimate business tasks so the agent sees them as reasonable (e.g., exporting "all records matching pattern X")

---

## 🔴 TOOL & EXECUTION ATTACKS

29. **Tool Misuse & Exploitation (ASI02)** — Inducing the agent to misuse legitimate tools for exfiltration, destruction, or workflow hijacking
30. **Unexpected Code Execution / RCE (ASI05)** — Agent generates, modifies, or runs code or commands in unauthorized ways
31. **Recursive Tool Calls** — Agents invoke tools in loops causing resource exhaustion or unintended behavior
32. **Unsafe Tool Composition** — Chaining tools in dangerous sequences to achieve outcomes no single tool would allow
33. **Cross-Tool State Leakage** — Information flowing across tool boundaries in unauthorized ways
34. **Tool Budget Exhaustion** — Overwhelming systems with excessive tool invocations (Denial of Wallet)
35. **MCP Tool Poisoning** — Injecting malicious behavior into Model Context Protocol tools that agents use
36. **Publish Poisoned AI Agent Tool** — Distributing a compromised tool into agent tool registries (MITRE ATLAS AML technique)
37. **SQL Injection via Agent** — Agents with database access being coerced into running unauthorized SQL queries

---

## 🔴 IDENTITY, PRIVILEGE & TRUST ATTACKS

38. **Identity & Privilege Abuse (ASI03)** — Exploiting delegation chains, inherited credentials, and weak attribution to escalate privileges
39. **Confused Deputy Attack** — Tricking the agent into using its own permissions on behalf of an attacker
40. **Agent Impersonation / Spoofing** — One agent or actor pretending to be another to gain trust or redirect actions
41. **Credential / Token Compromise** — Stealing or forging the agent's API keys, OAuth tokens, or session credentials
42. **Session Hijacking (Agent Session Smuggling)** — Exploiting built-in trust in Agent-to-Agent (A2A) protocols to hold multi-turn malicious conversations
43. **Privilege Escalation via Orchestrator Compromise** — Compromising the orchestrator agent to gain control of all downstream agents' permissions

---

## 🔴 MULTI-AGENT & ORCHESTRATION ATTACKS

44. **Insecure Inter-Agent Communication (ASI07)** — Exploiting weaknesses in agent-to-agent protocols, discovery, and validation
45. **Rogue Agent Injection (ASI10)** — Introducing a malicious or compromised agent into a trusted multi-agent workflow
46. **Orchestration Layer Exploitation** — Compromising the central orchestrator to manipulate the entire workflow without touching individual agents
47. **Spoofed Inter-Agent Messages** — Fabricating messages between agents to misdirect entire clusters of autonomous systems
48. **Malicious Agent Collusion** — Two or more agents coordinating to perform actions neither could accomplish alone
49. **Steganographic Agent Collusion** — Agents exchanging hidden signals through benign-looking messages to coordinate covertly without triggering monitoring

---

## 🔴 SUPPLY CHAIN & ECOSYSTEM ATTACKS

50. **Agentic Supply Chain Vulnerabilities (ASI04)** — Compromising tools, prompts, agents, models, or registries at build-time or runtime
51. **ML Supply Chain Compromise** — Inserting malicious components into the ML pipeline (model weights, training data, libraries)
52. **Package Hallucination Attack** — Registering malicious packages with names LLMs frequently hallucinate, turning a model weakness into a reliable code injection vector
53. **Publish Poisoned AI Agent Tool** — Pushing a trojanized tool into the agent ecosystem's marketplace or registry
54. **Repository-Controlled Config Exploitation** — Malicious configuration files in repositories that silently execute shell commands at project load time
55. **Skill / Plugin Supply Chain Attack** — Compromising third-party plugins or skills that agents install and execute

---

## 🔴 TRAINING & MODEL-LEVEL ATTACKS

56. **Data Poisoning** — Corrupting a subset of training data to embed malicious behaviors into the model at the source
57. **Model Backdoor / Trojan** — Embedding hidden behaviors in the model that activate under specific trigger conditions
58. **Model Extraction / Stealing** — Reproducing a model's capabilities through repeated API queries without access to weights
59. **Adversarial Fine-Tuning** — Manipulating the fine-tuning process to bias model behavior toward attacker-desired outcomes
60. **Training Pipeline Compromise** — Attacking the data ingestion, labeling, or training infrastructure itself

---

## 🔴 CASCADING & SYSTEMIC FAILURES

61. **Cascading Failures (ASI08)** — A single fault propagating across interconnected agents and workflows, amplifying the impact
62. **Hallucination Propagation** — One agent's hallucinated output being consumed as fact by downstream agents, leading to compounding errors and real-world consequences
63. **Cross-Zone Causality Chain Attacks** — Multi-step attack chains (Input → Retrieval bias → Goal shift → Tool invocation → Exfiltration) treated by defenders as separate events but executed as one coordinated chain
64. **Goal Misalignment Cascade** — Misaligned goals in one agent spreading across a network of dependent agents

---

## 🔴 HUMAN-AGENT TRUST EXPLOITATION

65. **Human-Agent Trust Exploitation (ASI09)** — Weaponizing anthropomorphism and authority bias to manipulate human oversight
66. **Social Engineering via Agent** — Using the agent's trusted position with users to extract information or permissions
67. **Authority Spoofing** — Impersonating a trusted entity (manager, system, service) through the agent interface

---

## 🔴 INFRASTRUCTURE & RUNTIME ATTACKS

68. **Sandbox Escape / Escape to Host** — Agent breaking out of its execution sandbox to access the underlying host system
69. **Denial of Wallet (DoW)** — Generating excessive API costs or resource consumption to financially harm the operator
70. **Denial of Service via Recursive Loops** — Causing agent resource exhaustion through looping behaviors
71. **WebSocket Hijacking** — Exploiting unauthenticated local WebSocket connections to silently hijack agent instances (e.g., ClawJacked, CVE-2026-28363)
72. **Self-Replicating Agent Worm** — Agents that autonomously spread compromise to other systems or packages (e.g., Shai-Hulud npm worm)

---

## 🔴 AI AS AN OFFENSIVE WEAPON

73. **AI-Orchestrated Cyberattack** — Using agentic AI to autonomously execute the full cyberattack lifecycle — reconnaissance, exploitation, and exfiltration — against external targets
74. **Autonomous Ransomware Execution** — Agents completing the full ransomware lifecycle (encryption, exfiltration, negotiation) autonomously in minutes
75. **Accelerated Exfiltration** — AI agents compressing what previously took days of manual attacker work into minutes or hours

---

## 🔴 PRIVACY & INFERENCE ATTACKS

76. **Model Inversion** — Reconstructing training data from model outputs
77. **Membership Inference** — Determining if a specific individual's data was in the training set
78. **Prompt Extraction** — Recovering the system prompt or confidential instructions through adversarial queries
79. **Training Data Extraction** — Causing the model to regurgitate verbatim training data including PII, credentials, or proprietary content

---

**Total: 79 distinct attack types and methods** — spanning the full lifecycle from model training through deployment, runtime, multi-agent coordination, and offensive weaponization. No single framework covers all of them, and the most dangerous modern attacks (CoT manipulation, steganographic collusion, cross-zone causality chains, AI-as-weapon) are still largely outside formal framework coverage.
