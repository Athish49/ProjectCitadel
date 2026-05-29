"use client";

import { useMemo, useState, useCallback } from "react";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  MarkerType,
  type Node,
  type Edge,
  type NodeMouseHandler,
} from "@xyflow/react";
import { AnimatePresence } from "framer-motion";
import "@xyflow/react/dist/style.css";

import { ARCH_NODES, ARCH_EDGES, NODE_SPECS } from "@/lib/data/architecture";
import type { ArchNode, NodeType, TrustLabel } from "@/lib/types/showcase";
import { ArchNodeComponent } from "./arch-node";
import { NodeDetail } from "./node-detail";

const LABEL_COLOR: Record<TrustLabel, string> = {
  public:       "#5BB5F2",
  personal:     "#F5B056",
  confidential: "#C879FF",
  secret:       "#F25B5B",
  untrusted:    "#8B96A8",
};

const NODE_TYPE_COLOR: Record<NodeType, string> = {
  agent:        "#5BB5F2",
  parser:       "#F5B056",
  orchestrator: "#C879FF",
  datastore:    "#4ADE80",
  filter:       "#8B96A8",
  external:     "#3A4452",
};

const NODE_POSITIONS: Record<string, { x: number; y: number }> = {
  console:           { x: 248, y: 0    },
  api:               { x: 248, y: 120  },
  ingress:           { x: 248, y: 260  },
  parser:            { x: 248, y: 400  },
  orchestrator:      { x: 248, y: 540  },
  intake_actor:      { x: -80, y: 720  },
  identity_verifier: { x: 130, y: 720  },
  claims_processor:  { x: 340, y: 720  },
  settlement_actor:  { x: 548, y: 720  },
  tool_registry:     { x: 228, y: 900  },
  data_layer:        { x: 228, y: 1060 },
  egress_filter:     { x: 248, y: 1200 },
  adversarial_agent: { x: -200, y: 330 },
};

const nodeTypes = { archNode: ArchNodeComponent };

const LEGEND_ITEMS: { label: TrustLabel; display: string }[] = [
  { label: "public",       display: "PUBLIC"       },
  { label: "personal",     display: "PERSONAL"     },
  { label: "confidential", display: "CONFIDENTIAL" },
  { label: "secret",       display: "SECRET"       },
  { label: "untrusted",    display: "UNTRUSTED"    },
];

export function ArchDiagram() {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const nodes: Node[] = useMemo(() =>
    ARCH_NODES.map((n) => ({
      id: n.id,
      type: "archNode" as const,
      position: NODE_POSITIONS[n.id] ?? { x: 0, y: 0 },
      data: n as unknown as Record<string, unknown>,
    })),
    []
  );

  const edges: Edge[] = useMemo(() =>
    ARCH_EDGES.map((e) => {
      const color = LABEL_COLOR[e.dataLabel ?? "public"];
      return {
        id: e.id,
        source: e.source,
        target: e.target,
        style: { stroke: color, strokeWidth: 1.5 },
        markerEnd: { type: MarkerType.ArrowClosed, color, width: 14, height: 14 },
      };
    }),
    []
  );

  const handleNodeClick: NodeMouseHandler = useCallback((_evt, node) => {
    setSelectedNodeId((prev) => (prev === node.id ? null : node.id));
  }, []);

  const handlePaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  const selectedSpec = selectedNodeId ? (NODE_SPECS[selectedNodeId] ?? null) : null;

  return (
    <div className="relative h-[calc(100vh-48px)] w-full overflow-hidden bg-[#0A0E14]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        onPaneClick={handlePaneClick}
        fitView
        fitViewOptions={{ padding: 0.12 }}
        style={{ background: "#0A0E14" }}
        defaultEdgeOptions={{ type: "default" }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          color="#1E2632"
          gap={24}
          size={1}
        />
        <Controls
          style={{
            background: "#0F141B",
            border: "1px solid #1E2632",
            borderRadius: 4,
          }}
        />
        <MiniMap
          nodeColor={(n) => {
            const archNode = n.data as unknown as ArchNode;
            return NODE_TYPE_COLOR[archNode.type] ?? "#8B96A8";
          }}
          style={{ background: "#0F141B", border: "1px solid #1E2632" }}
          maskColor="rgba(10,14,20,0.7)"
        />
      </ReactFlow>

      {/* data-flow legend */}
      <div className="pointer-events-none absolute bottom-4 left-4 rounded border border-[#1E2632] bg-[#0F141B]/90 px-3 py-2 backdrop-blur-sm">
        <div className="mb-1.5 font-mono text-[9px] uppercase tracking-widest text-[#8B96A8]">
          Data flow label
        </div>
        <div className="space-y-1">
          {LEGEND_ITEMS.map((item) => (
            <div key={item.label} className="flex items-center gap-1.5">
              <span
                className="h-px w-5 shrink-0"
                style={{ backgroundColor: LABEL_COLOR[item.label] }}
              />
              <span
                className="font-mono text-[9px]"
                style={{ color: LABEL_COLOR[item.label] }}
              >
                {item.display}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* node detail panel */}
      <AnimatePresence>
        {selectedSpec && (
          <NodeDetail
            key={selectedSpec.id}
            spec={selectedSpec}
            onClose={() => setSelectedNodeId(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
