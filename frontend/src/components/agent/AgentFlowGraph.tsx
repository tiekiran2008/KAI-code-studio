import React, { useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { CustomAgentNode } from './CustomAgentNode';

interface AgentFlowGraphProps {
  selectedAgentId: string | null;
  onSelectAgent: (id: string) => void;
}

export const AgentFlowGraph: React.FC<AgentFlowGraphProps> = ({
  selectedAgentId,
  onSelectAgent,
}) => {
  const nodeTypes = useMemo(() => ({ customAgent: CustomAgentNode }), []);

  const initialNodes = useMemo(
    () => [
      {
        id: 'supervisor',
        type: 'customAgent',
        position: { x: 300, y: 30 },
        data: {
          label: 'Supervisor Agent',
          agentType: 'supervisor',
          status: 'active',
          duration: 180,
          confidence: 0.98,
          errors: 0,
          isSelected: selectedAgentId === 'supervisor',
        },
      },
      {
        id: 'planner',
        type: 'customAgent',
        position: { x: 300, y: 160 },
        data: {
          label: 'Planner Agent',
          agentType: 'planner',
          status: 'online',
          duration: 240,
          confidence: 0.95,
          errors: 0,
          isSelected: selectedAgentId === 'planner',
        },
      },
      {
        id: 'context',
        type: 'customAgent',
        position: { x: 100, y: 290 },
        data: {
          label: 'Context Agent',
          agentType: 'context',
          status: 'online',
          duration: 85,
          confidence: 0.96,
          errors: 0,
          isSelected: selectedAgentId === 'context',
        },
      },
      {
        id: 'memory',
        type: 'customAgent',
        position: { x: 500, y: 290 },
        data: {
          label: 'Memory Agent',
          agentType: 'memory',
          status: 'online',
          duration: 120,
          confidence: 0.97,
          errors: 0,
          isSelected: selectedAgentId === 'memory',
        },
      },
      {
        id: 'reviewer',
        type: 'customAgent',
        position: { x: 200, y: 420 },
        data: {
          label: 'Code Reviewer Agent',
          agentType: 'reviewer',
          status: 'online',
          duration: 210,
          confidence: 0.94,
          errors: 0,
          isSelected: selectedAgentId === 'reviewer',
        },
      },
      {
        id: 'tool',
        type: 'customAgent',
        position: { x: 400, y: 420 },
        data: {
          label: 'Tool Adapter Agent',
          agentType: 'tool',
          status: 'online',
          duration: 150,
          confidence: 0.99,
          errors: 0,
          isSelected: selectedAgentId === 'tool',
        },
      },
    ],
    [selectedAgentId]
  );

  const initialEdges = useMemo(
    () => [
      { id: 'e-sup-plan', source: 'supervisor', target: 'planner', animated: true, style: { stroke: '#6366f1' } },
      { id: 'e-plan-ctx', source: 'planner', target: 'context', animated: true, style: { stroke: '#6366f1' } },
      { id: 'e-plan-mem', source: 'planner', target: 'memory', animated: true, style: { stroke: '#6366f1' } },
      { id: 'e-ctx-rev', source: 'context', target: 'reviewer', animated: true, style: { stroke: '#6366f1' } },
      { id: 'e-mem-tool', source: 'memory', target: 'tool', animated: true, style: { stroke: '#6366f1' } },
      { id: 'e-rev-sup', source: 'reviewer', target: 'supervisor', animated: true, style: { stroke: '#a855f7', strokeDasharray: '5,5' } },
      { id: 'e-tool-sup', source: 'tool', target: 'supervisor', animated: true, style: { stroke: '#a855f7', strokeDasharray: '5,5' } },
    ],
    []
  );

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  return (
    <div className="w-full h-[480px] rounded-2xl bg-slate-950 border border-slate-800 overflow-hidden relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={(_, node) => onSelectAgent(node.id)}
        fitView
      >
        <Background color="#334155" gap={16} size={1} />
        <Controls className="!bg-slate-900 !border-slate-800 !text-slate-200" />
      </ReactFlow>
    </div>
  );
};
