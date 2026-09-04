import { 
  Repository, 
  FileNode, 
  MemoryRecord, 
  ToolMetadata, 
  AnalyticsMetrics, 
  ConversationSession 
} from '../types';

export const MOCK_REPOSITORIES: Repository[] = [
  {
    id: 'repo-1',
    name: 'Software-Engineering-AI-Agent',
    owner: 'kelum',
    url: 'https://github.com/kelum/Software-Engineering-AI-Agent',
    defaultBranch: 'main',
    currentBranch: 'main',
    branches: ['main', 'feature/phase-9-frontend', 'dev'],
    indexingStatus: 'indexed',
    chunksCount: 1420,
    lastIndexedAt: '2026-07-29T18:45:00Z',
    language: 'Python / TypeScript',
    stars: 84,
  },
  {
    id: 'repo-2',
    name: 'fastapi-microservices-template',
    owner: 'organization',
    url: 'https://github.com/organization/fastapi-microservices-template',
    defaultBranch: 'main',
    currentBranch: 'main',
    branches: ['main', 'staging'],
    indexingStatus: 'indexed',
    chunksCount: 850,
    lastIndexedAt: '2026-07-28T14:10:00Z',
    language: 'Python',
    stars: 312,
  },
  {
    id: 'repo-3',
    name: 'react-design-system-core',
    owner: 'ui-team',
    url: 'https://github.com/ui-team/react-design-system-core',
    defaultBranch: 'master',
    currentBranch: 'master',
    branches: ['master', 'v2-beta'],
    indexingStatus: 'indexing',
    chunksCount: 620,
    lastIndexedAt: '2026-07-29T19:10:00Z',
    language: 'TypeScript',
    stars: 1240,
  }
];

export const MOCK_FILE_TREE: FileNode[] = [
  {
    id: 'f-1',
    name: 'backend',
    path: 'backend',
    type: 'directory',
    children: [
      {
        id: 'f-1-1',
        name: 'src',
        path: 'backend/src',
        type: 'directory',
        children: [
          {
            id: 'f-1-1-1',
            name: 'main.py',
            path: 'backend/src/main.py',
            type: 'file',
            language: 'python',
            content: `"""\nAI Software Engineering Agent — FastAPI Main Entrypoint\n"""\nfrom fastapi import FastAPI\nfrom fastapi.middleware.cors import CORSMiddleware\nfrom src.interfaces.api.v1.router import api_router\nfrom src.core.config import settings\n\napp = FastAPI(\n    title="AI Software Engineering Platform API",\n    version="1.0.0",\n)\n\napp.add_middleware(\n    CORSMiddleware,\n    allow_origins=["*"],\n    allow_credentials=True,\n    allow_methods=["*"],\n    allow_headers=["*"],\n)\n\napp.include_router(api_router, prefix="/api/v1")\n\n@app.get("/health")\nasync def health_check():\n    return {"status": "online", "version": "1.0.0"}\n`
          },
          {
            id: 'f-1-1-2',
            name: 'application',
            path: 'backend/src/application',
            type: 'directory',
            children: [
              {
                id: 'f-1-1-2-1',
                name: 'agents',
                path: 'backend/src/application/agents',
                type: 'directory',
                children: [
                  {
                    id: 'f-1-1-2-1-1',
                    name: 'supervisor.py',
                    path: 'backend/src/application/agents/supervisor.py',
                    type: 'file',
                    language: 'python',
                    content: `"""\nSupervisor Agent\nOrchestrates multi-agent plan execution and tool calling.\n"""\nimport time\nimport json\nfrom typing import Dict, Any\nfrom src.domain.interfaces.llm import ILLMProvider\nfrom src.domain.models.agents import AgentState, AgentType\n\nclass SupervisorAgent:\n    def __init__(self, llm_provider: ILLMProvider, tool_manager=None):\n        self.llm = llm_provider\n        self.tool_manager = tool_manager\n\n    async def execute(self, state: AgentState) -> Dict[str, Any]:\n        start = time.perf_counter()\n        query = state.get("query", "")\n        plan = state.get("plan")\n        # Tool orchestrations and final response synthesis...\n        return {"final_answer": "Synthesized architectural summary.", "next_agent": "__end__"}\n`
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  },
  {
    id: 'f-2',
    name: 'frontend',
    path: 'frontend',
    type: 'directory',
    children: [
      {
        id: 'f-2-1',
        name: 'package.json',
        path: 'frontend/package.json',
        type: 'file',
        language: 'json',
        content: `{\n  "name": "frontend",\n  "private": true,\n  "version": "0.1.0",\n  "dependencies": {\n    "react": "^19.0.0",\n    "zustand": "^5.0.3"\n  }\n}\n`
      }
    ]
  },
  {
    id: 'f-3',
    name: 'README.md',
    path: 'README.md',
    type: 'file',
    language: 'markdown',
    content: `# AI Software Engineering Platform\nProduction-grade multi-agent autonomous developer workspace.`
  }
];

export const MOCK_MEMORIES: MemoryRecord[] = [
  {
    id: 'mem-1',
    userId: 'usr-admin-1',
    repositoryId: 'repo-1',
    memoryType: 'long_term',
    content: 'User prefers Python clean architecture with explicit domain interfaces, type hints, and FastAPI dependency injection.',
    importanceScore: 0.95,
    recencyBonus: 0.12,
    createdAt: '2026-07-28T10:00:00Z',
    updatedAt: '2026-07-29T14:00:00Z',
    techStack: ['Python', 'FastAPI', 'SQLAlchemy', 'Qdrant'],
    isEncrypted: true
  },
  {
    id: 'mem-2',
    userId: 'usr-admin-1',
    repositoryId: 'repo-1',
    memoryType: 'repository',
    content: 'Repository contains a hybrid retrieval engine combining BM25 keyword matching with dense Qdrant embeddings and RRF reranking.',
    importanceScore: 0.88,
    recencyBonus: 0.08,
    createdAt: '2026-07-29T09:30:00Z',
    updatedAt: '2026-07-29T18:00:00Z',
    techStack: ['Qdrant', 'FastAPI', 'LangGraph'],
    isEncrypted: false
  },
  {
    id: 'mem-3',
    userId: 'usr-admin-1',
    repositoryId: 'repo-1',
    memoryType: 'episodic',
    content: 'Resolved Pytest import issue by ensuring PYTHONPATH env var includes workspace root during execution.',
    importanceScore: 0.76,
    recencyBonus: 0.05,
    createdAt: '2026-07-29T14:05:00Z',
    updatedAt: '2026-07-29T14:05:00Z',
    techStack: ['Pytest'],
    isEncrypted: false
  }
];

export const MOCK_TOOLS: ToolMetadata[] = [
  {
    name: 'github_read',
    description: 'Reads GitHub repository branches, commits, pull requests, issues, and file contents.',
    permissions: 'read_only',
    timeoutSeconds: 15.0,
    retryMax: 2,
    version: '1.0.0',
    inputSchema: {
      owner: 'string',
      repo: 'string',
      action: 'branches | commits | pulls | issues | content'
    }
  },
  {
    name: 'local_fs_read',
    description: 'Safely inspects local workspace files, directories, and glob patterns.',
    permissions: 'read_only',
    timeoutSeconds: 10.0,
    retryMax: 1,
    version: '1.0.0',
    inputSchema: {
      action: 'read_file | list_dir | search',
      path: 'string'
    }
  },
  {
    name: 'docs_search',
    description: 'Queries indexed documentation, API references, and architecture guides using RAG.',
    permissions: 'read_only',
    timeoutSeconds: 20.0,
    retryMax: 2,
    version: '1.0.0',
    inputSchema: {
      query: 'string',
      repo_id: 'string'
    }
  },
  {
    name: 'database_read',
    description: 'Reads repository metadata, user memory records, and conversational logs.',
    permissions: 'restricted',
    timeoutSeconds: 10.0,
    retryMax: 1,
    version: '1.0.0',
    inputSchema: {
      action: 'repo_metadata | conversation_history | memory_search',
      user_id: 'string'
    }
  },
  {
    name: 'repo_diff',
    description: 'Compares branches and commits using safe read-only git diff commands.',
    permissions: 'read_only',
    timeoutSeconds: 15.0,
    retryMax: 1,
    version: '1.0.0',
    inputSchema: {
      action: 'compare_commits | changed_files | summary',
      base: 'string',
      head: 'string'
    }
  }
];

export const MOCK_ANALYTICS: AnalyticsMetrics = {
  retrievalLatencyP50: 42.5,
  retrievalLatencyP95: 118.2,
  retrievalLatencyP99: 245.0,
  totalTokensUsed: 184500,
  agentExecutionsCount: 428,
  toolInvocationsCount: 152,
  memoryHitRate: 91.4,
  activeSessionsCount: 14,
  averageConfidence: 0.94
};

export const MOCK_SESSIONS: ConversationSession[] = [
  {
    id: 'session-1',
    title: 'Phase 9 Frontend Architecture & Workspace Design',
    repositoryId: 'repo-1',
    createdAt: '2026-07-29T18:00:00Z',
    updatedAt: '2026-07-29T19:30:00Z',
    messages: [
      {
        id: 'msg-1',
        role: 'user',
        content: 'Explain the tool calling framework implemented in Phase 8 and how the Supervisor routes calls.',
        timestamp: '2026-07-29T18:01:00Z'
      },
      {
        id: 'msg-2',
        role: 'assistant',
        content: `### Tool Calling Framework Overview

The **Phase 8 Tool Calling Framework** allows the multi-agent system to safely interact with developer tools (GitHub, local filesystem, documentation, DB, and git diff) with strict read-only guarantees.

#### Architecture Highlights
1. **Tool Registry**: Manages tool metadata and Role-Based Access Control (\`PermissionLevel\`).
2. **Tool Manager**: Handles timeouts (\`asyncio.wait_for\`), retries with exponential backoff, and auditing.
3. **Supervisor Agent**: Fetches tool schemas, passes them to the LLM, parses function calls, and executes tool tasks in parallel before synthesizing the final response.`,
        timestamp: '2026-07-29T18:01:05Z',
        citations: [
          {
            file_path: 'backend/src/application/agents/supervisor.py',
            start_line: 15,
            end_line: 45,
            snippet: 'class SupervisorAgent:\n  def _get_available_tools(self):\n    return self.tool_manager.list_tools()'
          }
        ],
        agentTraces: [
          { agent: 'supervisor', action: 'routed_to_planner', latency_ms: 12.4, confidence: 0.98 },
          { agent: 'planner', action: 'plan_created', latency_ms: 240.1, confidence: 0.95 },
          { agent: 'context', action: 'rag_search_complete', latency_ms: 85.2, confidence: 0.96 },
          { agent: 'supervisor', action: 'executed_tools', latency_ms: 310.0, confidence: 0.97 },
          { agent: 'evaluation', action: 'quality_passed', latency_ms: 15.0, confidence: 0.99 },
          { agent: 'supervisor', action: 'synthesized_final_answer', latency_ms: 180.5, confidence: 0.98 }
        ],
        toolCalls: [
          {
            tool_name: 'local_fs_read',
            caller_agent: 'SupervisorAgent',
            arguments: { action: 'read_file', path: 'backend/src/application/agents/supervisor.py' },
            success: true,
            latency_ms: 14.2,
            timestamp: '2026-07-29T18:01:03Z'
          }
        ]
      }
    ]
  }
];
