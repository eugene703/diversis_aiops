import os
import chainlit as cl
from langchain_core.messages import HumanMessage, BaseMessage
from src.agent import agent


@cl.on_message
async def handle_message(message):
    # Build the initial HumanMessage (include parquet path in extra args)
    user_msg = HumanMessage(
        content=message.content,
    )

    # Stream through the agent
    for chunk in agent.stream([user_msg], stream_mode="updates"):
        # The chunk can be:
        #  • an instance of BaseMessage (e.g. AIMessage)
        #  • a dict mapping tool names to BaseMessage results
        if isinstance(chunk, BaseMessage):
            text = chunk.content
        elif isinstance(chunk, dict):
            # pick out all the BaseMessage values and concatenate
            texts = []
            for val in chunk.values():
                if isinstance(val, BaseMessage):
                    texts.append(val.content)
            text = "\n".join(texts)
        else:
            # fallback
            text = str(chunk)

        await cl.Message(content=text).send()
