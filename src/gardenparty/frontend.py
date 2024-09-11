"""
Gradio frontend
"""
import base64
import hashlib
import logging
from pathlib import Path
from pprint import pprint
import random
import time
import gradio as gr
from gradio import ChatMessage, MessageDict
import os

import requests

from gardenparty.backend import describe_image, generate_themed_prompt, get_templates, image_to_image
from gardenparty.preprocess import autocrop, autocrop_and_straighten, save_image_as

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

BTN_STRAIGHTEN = "Straighten"

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

def get_image_themes():

    return [
        Path(f).stem for f in get_templates()["files"]
    ]

def process(chat_history, img_input, options, theme):

    yield None, gr.Image(img_input, type="filepath", interactive=False)
    
    time.sleep(10)
    
    for r in chatbot_acquire(chat_history, img_input, options, theme):
        # TODO detect last history message and update the toolbar
        yield r, gr.Image(img_input, type="filepath", interactive=False)


def chatbot_acquire(chat_history, img_input, options, theme):

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

        if BTN_STRAIGHTEN in options:
            autocrop_and_straighten(img_input, target_file)
        else:
            autocrop(img_input, target_file)
        
        chat_history += [
            ChatMessage(
                role="system",
                content=f"Image: {target_file!r}",
            )
        ]
        
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
        ),
        ChatMessage(
            role="system",
            content=f"{llm_response}"
        )
    ]

    yield ui_chatbot(chat_history)
    
    yield from chatbot_imggen(chat_history, theme="robot", image=fname)

    return


def chatbot_imggen(chat_history, theme, image):
    # Get last system message, use it as prompt
    for m in reversed(chat_history):
        if m.role == "system":
            prompt = m.content
            break
    generative_prompt = generate_themed_prompt(theme, prompt)
    
    positive = generative_prompt["prompt"]
    negative = generative_prompt["negative_prompt"]
    
    chat_history += [ChatMessage(
            role="assistant",
            content=f"Generating image with theme {theme!r} and using the following promt:\n\n{positive!r}\n\n{negative!r}"
        )]

    yield ui_chatbot(chat_history)

    img2img = image_to_image(image, positive, negative)
    
    chat_history += [ChatMessage(
        role="user",
        content=img2img['output_filename']
    )]

    yield ui_chatbot(chat_history)


def gra_chatapp():
    """
    Chat interface for the app.
    """
    with gr.Blocks(fill_height=True, title="Garden party AI patcher") as app:

            # with gr.Row(variant="panel"):
            #     reset_btn = gr.Button("Reset")
            #     undo_btn = gr.Button("Undo")
            #     clear_btn = gr.Button("Clear")

        with gr.Row():
            
            with gr.Column():
                img_input = gr.Image(
                    #height=200,
                    #width=200,
                    type="filepath",
                    sources=["webcam", "upload"],
                    label="Upload image",
                    mirror_webcam=False,
                    show_label=False)

            with gr.Column():
                options = gr.CheckboxGroup(
                    [BTN_STRAIGHTEN],
                    value=[BTN_STRAIGHTEN],
                    label="Options",
                    show_label=True,
                )
                
                themes = get_image_themes()
                choices = random.sample(themes, 5)
                theme = gr.Dropdown(
                    choices=choices,
                    value=choices[0],
                    label="Theme",
                    show_label=True,
                )
                
                email = gr.Textbox(label="📧 Email", placeholder="jori.ajola@jyu.fi", info="(Optional) Email address is only used to inform winners of the contest")

        with gr.Row():
            
            chatbot = ui_chatbot()

        # First stage input
        img_input.input(process, inputs=[chatbot, img_input, options, theme], outputs=[chatbot, img_input])
    
    return app

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    app = gra_chatapp()
    app.launch(show_api=False, share=False)
