"""
Gradio frontend
"""
import base64
import hashlib
import logging
import time
import gradio as gr
from gradio import ChatMessage, MessageDict
import os

import requests

from gardenparty.backend import describe_image
from gardenparty.preprocess import autocrop, autocrop_and_straighten, save_image_as

from uuid import uuid4

from gardenparty.app import settings

logger = logging.getLogger(__name__)

# Disable telemetry
os.environ.setdefault("GRADIO_TELEMETRY", "0")
os.environ.setdefault('GRADIO_ANALYTICS_ENABLED', "0")
os.environ.setdefault("GRADIO_SERVER_NAME", "0.0.0.0")

DESCRIPTION = r"""
## IT-Faculty Garden Party 2024: The AI patcher

1. 📷 📂 Acquire an image using the camer or upload an image 
2. 📧 🏅 (Optional) Fill in your email address to participate in the contest
3. 🤖 ⚙️ Let the AI patcher do its magic 
4. 🖼️ 🗳️ Vote for the best AI-patched image
"""

def ui_chatbot(history=[]):
    chatbot = gr.Chatbot(
        history,
        type="messages",
        label="Patcher 3000",
        placeholder=DESCRIPTION,
        show_label=False,
        scale=1,
    )
    return chatbot


def get_sketch_description(image) -> str:
    # TODO  HTTP call
    r = describe_image(image)
    return r["reply"]


def acquire(chat_history, img_input, auto_adjust=False):

    for r in chatbot_acquire(chat_history, img_input, auto_adjust):
        # TODO detect last history message and update the toolbar
        yield r, gr.Image(img_input, type="filepath", interactive=False)

def chatbot_acquire(chat_history, img_input, auto_adjust=False):

    # Use sha256 hash of the image as filename
    with open(img_input, "rb") as fd:
        sha = hashlib.sha256(fd.read()).hexdigest()
        fname = f"{sha}.webp"

    target_file = settings.INSTANCE_PATH / "original" / fname

    try:
        chat_history += [
            ChatMessage(
                role="assistant",
                content=f"Image received. Processing...",
            )
        ]

        yield ui_chatbot(chat_history)

        if auto_adjust:
            autocrop_and_straighten(img_input, target_file)
        else:
            autocrop(img_input, target_file)
            save_image_as(img_input, target_file)
        
        # chat_history += [
        #     ChatMessage(
        #         role="assistant",
        #         content=gr.Image(target_file, type="filepath", interactive=False)
        #     )
        # ]

        chat_history += [
            ChatMessage(
                role="assistant",
                content="Do you wish to provide an email address to participate in the contest?"
            ),
            ChatMessage(
                role="user",
                content="No thanks TODO"
            )
        ]

    except Exception as e:

        chat_history += [
            ChatMessage(
                role="assistant",
                content=f"An error occurred while processing the image: {e}",
            )
        ]

    chat_history += [
        ChatMessage(
            role="assistant",
            content="Looking at the picture... 🧐",
        )
    ]

    yield ui_chatbot(chat_history)

    llm_response = get_sketch_description(fname)

    chat_history += [
        ChatMessage(
            role="assistant",
            content=f"Ok 👍. {llm_response}"
        )
    ]

    yield ui_chatbot(chat_history)

    return

def gr_app():
    with gr.Blocks(theme=gr.themes.Soft()) as app:
        log_messages = gr.State([])
        with gr.Row():
            gr.Markdown(DESCRIPTION)
            email = gr.Textbox(label="Email", placeholder="Email", info="Email address is only used to inform winners of the contest")
        with gr.Row():
            with gr.Column():
                img_input = gr.Image(type="filepath", sources=["webcam", "upload"], label="Acquire Image")
            with gr.Column():
                img_output = gr.Image(type="filepath", label="Generated Image", sources=[], interactive=False)
        with gr.Row() as toolbar:
            with gr.Column():
                auto_adjust = gr.Checkbox(True, label="Auto adjust", info="Auto adjust the image")

        img_input.input(acquire, inputs=[img_input, auto_adjust], outputs=[img_output])
    return app


def gra_chatapp():
    """
    Chat interface for the app.
    """
    with gr.Blocks(fill_height=True, title="Garden party AI patcher", fill_width=True) as app:

            chatbot = ui_chatbot()
            with gr.Row(variant="panel"):
                reset_btn = gr.Button("Reset")
                undo_btn = gr.Button("Undo")
                clear_btn = gr.Button("Clear")

            with gr.Row() as actionbar:
                img_input = gr.Image(
                    height=200,
                    width=200,
                    type="filepath",
                    sources=["webcam", "upload"],
                    label="Upload image",
                    mirror_webcam=False,
                    show_label=False)

                options = gr.CheckboxGroup(
                    ["Staighten"],
                    label="Options",
                    show_label=True,
                )
                # img_input = gr.ImageEditor(
                #     type="filepath",
                #     sources=["webcam"],
                #     label="Provide a sketch",
                #     elem_id="img_input")
                # img_output = gr.Image(type="filepath", label="Generated Image", sources=[], interactive=False)

            img_input.input(acquire, inputs=[chatbot, img_input], outputs=[chatbot, img_input])
    
    return app

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    app = gra_chatapp()
    app.launch(show_api=False, share=False)
