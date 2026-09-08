"""Planner agent: turns a high-level request into executable, testable steps."""
from codeforge.core.state import PlanStep, TaskPlan, TaskState, TaskPhase
from codeforge.observability.tracer import TraceCollector

class PlannerAgent:
    def run(self, state: TaskState, tracer: TraceCollector) -> TaskState:
        span = tracer.start_span("agent.planner", span_type="agent")
        state.phase = TaskPhase.PLAN
        request = state.user_request.strip()
        state.plan = TaskPlan(
            summary=f"Implement and validate: {request}",
            acceptance_criteria=["Implementation is complete", "Tests pass", "Security checks pass", "Changes are reviewable"],
            steps=[
                PlanStep(step_id=1, description="Understand the repository and locate relevant code", acceptance_criteria="Relevant files and dependencies identified"),
                PlanStep(step_id=2, description="Design the smallest safe implementation", acceptance_criteria="Architecture and interfaces are explicit"),
                PlanStep(step_id=3, description="Implement the change", acceptance_criteria="Code changes are isolated and readable"),
                PlanStep(step_id=4, description="Run tests and diagnose failures", acceptance_criteria="Tests pass or failures are explicitly reported"),
                PlanStep(step_id=5, description="Review and security-scan the change", acceptance_criteria="No blocking review/security findings remain"),
            ],
        )
        state.log("Created implementation plan.")
        tracer.end_span(span.span_id)
        return state
