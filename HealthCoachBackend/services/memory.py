from collections import deque

# Mémoire courte : 5 derniers échanges max
conversation_memory = {}

MAX_TURNS = 5


def get_memory(session_id: str):
    return conversation_memory.get(session_id, deque(maxlen=MAX_TURNS))


def add_to_memory(session_id: str, role: str, content: str):
    if session_id not in conversation_memory:
        conversation_memory[session_id] = deque(maxlen=MAX_TURNS)

    conversation_memory[session_id].append({"role": role, "content": content})
