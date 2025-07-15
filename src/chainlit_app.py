import os
import chainlit as cl
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage, ToolMessage
from src.agent import agent

# Helper: get the session's message history (per user)
def get_history():
    return cl.user_session.get("history") or []

def set_history(history):
    cl.user_session.set("history", history)

@cl.on_message
async def handle_message(message):
    # 1. Retrieve and update history for this session
    history = get_history()
    user_msg = HumanMessage(content=message.content)
    history.append(user_msg)

    # 2. Stream agent with full history
    for chunk in agent.stream(history, stream_mode="updates"):
        # If it's a dict, try to find the first AI/Tool message (Anthropic-style tools)
        if isinstance(chunk, dict):
            # Handle each result in the dict
            for val in chunk.values():
                if isinstance(val, BaseMessage):
                    # If Anthropic, content is a list of {"type":"text", "text":...}
                    if isinstance(val.content, list):
                        for item in val.content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                await cl.Message(content=item.get("text")).send()
                    elif isinstance(val.content, str):
                        await cl.Message(content=val.content).send()
                    else:
                        await cl.Message(content=str(val.content)).send()
                    # Add to history
                    history.append(val)
        elif isinstance(chunk, BaseMessage):
            # Direct agent/AI message
            if isinstance(chunk.content, list):
                for item in chunk.content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        await cl.Message(content=item.get("text")).send()
            elif isinstance(chunk.content, str):
                await cl.Message(content=chunk.content).send()
            else:
                await cl.Message(content=str(chunk.content)).send()
            # Add to history
            history.append(chunk)
        # else: ignore tool dict outputs for now

    # 3. Save updated history for this session
    set_history(history)
