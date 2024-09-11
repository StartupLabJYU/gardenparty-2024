"""
Gradio frontend
"""
import csv
import hashlib
import logging
from pathlib import Path
import random
import time
from uuid import uuid4
import gradio as gr
from gradio import ChatMessage
import os

import requests

from gardenparty.backend import describe_image, generate_themed_prompt, get_templates, image_to_image
from gardenparty.preprocess import autocrop, autocrop_and_straighten

from gardenparty.app import settings

logger = logging.getLogger(__name__)

# Disable telemetry
os.environ.setdefault("GRADIO_TELEMETRY", "0")
os.environ.setdefault('GRADIO_ANALYTICS_ENABLED', "0")
os.environ.setdefault("GRADIO_SERVER_NAME", "0.0.0.0")

DESCRIPTION = r"""
## IT-Faculty Garden Party 2024: The AI patcher

0. 🔄 (Refresh the page if previous messages are still visible)
1. 🎨 🫶 Draw an patch design for IT Faculty with the theme of _Unity_
2. 📷 📂 Acquire the design using the camera or upload an image 
3. 📧 🏅 (_Optional_) Fill in your email address to participate in the contest
4. 🤖 ⚙️ Let the AI patcher do its magic 
5. 🖼️ 🗳️ Vote for the best AI-patched image
6. 🎉 🏆 (_Optional_) Win prizes! 
"""

BTN_ON_PREMISES = "Agora event crop"
BTN_STRAIGHTEN = "Auto straighten"

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

def save_email(img, email):
    """
    Write email to file
    """
    with open(settings.INSTANCE_PATH / "emails.csv", "a") as f:
        w = csv.writer(f)
        w.writerow([Path(img).stem, email])


def process(chat_history, img_input, options, theme, email):


    if not img_input:
        gr.Error("No image provided. If you attempted camera, please tap the camera button in the preview window.")
        return

    gr.Info("Starting image processing...", duration=5)

    # Use sha256 hash of the image as filename
    with open(img_input, "rb") as fd:
        #sha = hashlib.sha256(fd.read()).hexdigest()
        sha = uuid4()
        fname = f"{sha}.jpg"

    target_file = settings.INSTANCE_PATH / "original" / fname

    try:
        chat_history += [
            ChatMessage(
                role="assistant",
                content=f"Image received. Processing...",
            )
        ]

        yield ui_chatbot(chat_history), gr.Image(img_input, type="filepath", interactive=False)

        if BTN_STRAIGHTEN in options:
            autocrop_and_straighten(img_input, target_file)
        else:
            autocrop(img_input, target_file)

        yield ui_chatbot(chat_history), gr.Image(target_file, type="filepath", interactive=False)

        
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
            )
        ]
        if email:
            chat_history += [
                ChatMessage(
                    role="user",
                    content="✅ Sure!"
                )
            ]
            save_email(fname, email)
        else:
            chat_history += [
                ChatMessage(
                    role="user",
                    content="⛔ No thanks."
                )
            ]

        yield ui_chatbot(chat_history), gr.Image(target_file, type="filepath", interactive=False)

    except Exception as e:

        chat_history += [
            ChatMessage(
                role="assistant",
                content=f"An error occurred while processing the image: {e}",
            )
        ]
        gr.Error("An error occurred while processing the image.")
        yield ui_chatbot(chat_history), gr.Image(target_file, type="filepath", interactive=False)
        return 

    chat_history += [
        ChatMessage(
            role="assistant",
            content="Looking at the picture... 🧐",
        )
    ]

    yield ui_chatbot(chat_history), gr.Image(target_file, type="filepath", interactive=False)

    llm_response = get_sketch_description(fname)

    chat_history += [
        ChatMessage(
            role="user",
            content=f"{llm_response}"
        ),
        ChatMessage(
            role="assistant",
            content="Ok 👍."
        )
    ]

    yield ui_chatbot(chat_history), gr.Image(target_file, type="filepath", interactive=False)

    generative_prompt = generate_themed_prompt(theme, llm_response)
    
    positive = generative_prompt["prompt"]
    negative = generative_prompt["negative_prompt"]
    
    chat_history += [ChatMessage(
            role="assistant",
            content=f"Generating image with theme {theme!r} and using the following promt:\n\n{positive!r}\n\n{negative!r}"
        )]

    yield ui_chatbot(chat_history), gr.Image(target_file, type="filepath", interactive=False)

    img2img = image_to_image(fname, positive, negative)
    
    chat_history += [ChatMessage(
        role="user",
        content=img2img['output_filename']
    )]

    chat_history += [ChatMessage(
        role="user",
        content="**Voting**: You can [now go and vote for your favorite – or own – AI-patched image!](https://itk-pj-voting.byteboat.fi/)\n![](https://itk-pj-voting.byteboat.fi/static/voting_qr.png)"
    )]

    yield ui_chatbot(chat_history), gr.Image(img2img['output_filename'], type="filepath", interactive=False)

    gr.Info("ℹ️ Image has been created! Go vote!", duration=10)
    return 


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
                
                themes = get_image_themes()
                    # Always include the "drawing" as the first option
                choices = random.sample(themes, 5)
                
                if "drawing" in choices:
                    themes.remove("drawing")
                choices.insert(0, "drawing")

                theme = gr.Dropdown(
                    choices=choices,
                    value=choices[0],
                    label="Theme",
                    show_label=True,
                )

                email = gr.Textbox(label="📧 (Optional) Email or username", placeholder="jori.ajola@jyu.fi", info="Email address is only used to inform winners of the contest")

                options = gr.CheckboxGroup(
                    [BTN_STRAIGHTEN],
                    value=[],
                    label="Options",
                    show_label=True,
                )

        with gr.Row():
            submit = gr.Button("Submit")
        with gr.Row():
            
            chatbot = ui_chatbot()

        submit.click(process, inputs=[chatbot, img_input, options, theme, email], outputs=[chatbot, img_input])
    
    return app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    app = gra_chatapp()
    app.launch(show_api=False, share=False)
