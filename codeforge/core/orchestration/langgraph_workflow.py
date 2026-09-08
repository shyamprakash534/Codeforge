"""Optional LangGraph execution adapter for the CodeForge workflow."""
class LangGraphWorkflow:
    def __init__(self, orchestrator):
        try: from langgraph.graph import StateGraph, START, END
        except ImportError as exc: raise RuntimeError("Install the 'langgraph' extra to use this adapter") from exc
        self.orchestrator=orchestrator; graph=StateGraph(dict)
        graph.add_node('plan',lambda s:self._step(s,'planner')); graph.add_node('research',lambda s:self._step(s,'researcher'))
        graph.add_node('architect',lambda s:self._step(s,'architect')); graph.add_node('test',lambda s:self._step(s,'tester'))
        graph.add_edge(START,'plan'); graph.add_edge('plan','research'); graph.add_edge('research','architect'); graph.add_edge('architect','test'); graph.add_edge('test',END)
        self.graph=graph.compile()
    def _step(self,state,name):
        # The full deterministic orchestrator remains the source of truth; this adapter
        # exposes the agent stages to LangGraph without duplicating business logic.
        state.setdefault('stages',[]).append(name); return state
    def invoke(self,request): return self.graph.invoke({'request':request,'stages':[]})
