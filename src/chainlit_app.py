import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import chainlit as cl
from chainlit.element import Image
from langchain_core.messages import HumanMessage, BaseMessage
from src.agent import agent

# --- Helpers for session history ---
def get_history():
    return cl.user_session.get("history") or []

def set_history(history):
    cl.user_session.set("history", history)

def _is_base64_image(s: str):
    if not isinstance(s, str):
        return False
    return s[:10].startswith("iVBOR") and len(s) > 1000

def _to_chainlit_image(b64str: str, name="Chart"):
    if not b64str.startswith("data:image"):
        b64str = f"data:image/png;base64,{b64str}"
    return Image(content=b64str, name=name)

async def _handle_base_or_aimessage(val, history):
    """Helper to handle BaseMessage (AIMessage, ToolMessage) for Chainlit."""
    content = getattr(val, "content", None)
    sent = False
    # Anthropic-style: list of dicts (could be text or image)
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    await cl.Message(content=item.get("text")).send()
                    sent = True
                elif item.get("type") == "image":
                    b64 = item.get("data", "")
                    if _is_base64_image(b64):
                        img = _to_chainlit_image(b64)
                        await cl.Message(content="Generated chart:", elements=[img]).send()
                        sent = True
    elif isinstance(content, str):
        if _is_base64_image(content):
            img = _to_chainlit_image(content)
            await cl.Message(content="Generated chart:", elements=[img]).send()
        else:
            await cl.Message(content=content).send()
        sent = True
    elif content is not None:
        await cl.Message(content=str(content)).send()
        sent = True
    if sent:
        history.append(val)

@cl.on_message
async def handle_message(message):
    history = get_history()
    user_msg = HumanMessage(content=message.content)
    history.append(user_msg)
    for chunk in agent.stream(history, stream_mode="updates"):
        # Show any message to user (and add to history) using our helper
        if isinstance(chunk, BaseMessage):
            await _handle_base_or_aimessage(chunk, history)
        elif isinstance(chunk, dict):
            for val in chunk.values():
                if isinstance(val, BaseMessage):
                    await _handle_base_or_aimessage(val, history)
    set_history(history)
