import * as React from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import "./flow.css";

export type { Edge as FlowEdge, Node as FlowNode } from "@xyflow/react";

/**
 * A flowchart / node editor (React Flow, @xyflow/react): workflows, org charts, process maps, decision trees. Boxes can
 * be dragged; with `editable` people can join two boxes by dragging from one edge dot to another. Example:
 *   <Flow nodes={[{ id: "a", position: { x: 0, y: 0 }, data: { label: "Order placed" } },
 *                 { id: "b", position: { x: 0, y: 120 }, data: { label: "Packed" } }]}
 *         edges={[{ id: "a-b", source: "a", target: "b" }]} onChange={(n, e) => save(n, e)} />
 */
export function Flow({
  nodes: startNodes,
  edges: startEdges,
  editable = true,
  onChange,
  height = 480,
  miniMap = false,
}: {
  nodes: Node[];
  edges: Edge[];
  editable?: boolean;
  /** called after a box moves or two boxes are joined (save the chart here) */
  onChange?: (nodes: Node[], edges: Edge[]) => void;
  height?: number;
  miniMap?: boolean;
}) {
  const [nodes, , onNodesChange] = useNodesState(startNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(startEdges);
  const changed = React.useRef(onChange);
  changed.current = onChange;
  const onConnect = React.useCallback(
    (c: Connection) => setEdges((es) => {
      const next = addEdge(c, es);
      changed.current?.(nodes, next);
      return next;
    }),
    [setEdges, nodes],
  );
  return (
    <div className="hoola-flow rounded-card border border-line bg-surface" style={{ height }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={editable ? onNodesChange : undefined}
        onEdgesChange={editable ? onEdgesChange : undefined}
        onConnect={editable ? onConnect : undefined}
        onNodeDragStop={() => changed.current?.(nodes, edges)}
        nodesDraggable={editable}
        nodesConnectable={editable}
        fitView
        proOptions={{ hideAttribution: false }}
      >
        <Background gap={20} />
        <Controls showInteractive={false} />
        {miniMap && <MiniMap pannable zoomable />}
      </ReactFlow>
    </div>
  );
}
