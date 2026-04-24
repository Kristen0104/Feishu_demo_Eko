"""
Agent 状态机模块
定义 Agent 处理流程的状态转换：IDLE -> ANALYZING -> RETRIEVING -> GENERATING -> SYNCING -> COMPLETED
"""
from enum import Enum


class AgentState(str, Enum):
    IDLE = "IDLE"
    ANALYZING = "ANALYZING"
    RETRIEVING = "RETRIEVING"
    GENERATING = "GENERATING"
    SYNCING = "SYNCING"
    COMPLETED = "COMPLETED"


# State transitions
VALID_TRANSITIONS = {
    AgentState.IDLE: [AgentState.ANALYZING],
    AgentState.ANALYZING: [AgentState.RETRIEVING, AgentState.GENERATING],
    AgentState.RETRIEVING: [AgentState.GENERATING],
    AgentState.GENERATING: [AgentState.SYNCING],
    AgentState.SYNCING: [AgentState.COMPLETED],
    AgentState.COMPLETED: [AgentState.IDLE],
}


class AgentStateMachine:
    def __init__(self):
        self.current_state = AgentState.IDLE

    def transition(self, new_state: AgentState) -> bool:
        if new_state in VALID_TRANSITIONS.get(self.current_state, []):
            self.current_state = new_state
            return True
        return False

    def reset(self):
        self.current_state = AgentState.IDLE

    def can_transition(self, new_state: AgentState) -> bool:
        return new_state in VALID_TRANSITIONS.get(self.current_state, [])


# Global state machine instance
agent_state_machine = AgentStateMachine()
