import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { CodeBlock } from "@/components/primitives/code-block";

const meta: Meta<typeof CodeBlock> = {
  title: "Primitives/CodeBlock",
  component: CodeBlock,
  parameters: { layout: "padded", backgrounds: { default: "dark" } },
};
export default meta;

type Story = StoryObj<typeof CodeBlock>;

export const TypeScript: Story = {
  args: {
    lang: "typescript",
    filename: "envelope.ts",
    code: `import { sign } from "@noble/secp256k1";

export async function signEnvelope(
  payload: AgentMessage,
  privateKey: Uint8Array
): Promise<SignedEnvelope> {
  const digest = await sha256(JSON.stringify(payload));
  const sig = await sign(digest, privateKey);
  return { payload, signature: bytesToHex(sig) };
}`,
  },
};

export const Python: Story = {
  args: {
    lang: "python",
    filename: "verify.py",
    code: `from coincurve import PublicKey

def verify_envelope(envelope: dict, pub_key_hex: str) -> bool:
    payload_bytes = json.dumps(envelope["payload"]).encode()
    digest = hashlib.sha256(payload_bytes).digest()
    pub = PublicKey(bytes.fromhex(pub_key_hex))
    return pub.verify(bytes.fromhex(envelope["signature"]), digest)`,
  },
};

export const JSON: Story = {
  args: {
    lang: "json",
    filename: "capability-token.json",
    code: `{
  "sub": "agent:claims-processor",
  "iss": "orchestrator",
  "iat": 1748477200,
  "exp": 1748480800,
  "scope": ["claims:read", "claims:write"],
  "trust_level": "confidential",
  "sig": "3045022100..."
}`,
  },
};

export const NoFilename: Story = {
  args: {
    lang: "bash",
    code: `# Run the full integration test suite
make test-attack-suite
`,
  },
};
