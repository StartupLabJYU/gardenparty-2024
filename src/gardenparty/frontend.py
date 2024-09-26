"""
Gradio frontend
"""
from fastapi import FastAPI
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
## Tutkijoiden yö: Tekoälypiirros

0. 🔄 (Päivitä sivu jos edellinen kuva on näkyvillä)
1. 🎨 🫶 Piirrä mieleisesi kuva paperille
2. 📷 📂 Skannaa kuva kännykän kameralla
3. 🤖 ⚙️ Anna tekoälyn tehdä taikojansa
4. 🖼️ 🗳️ Äänestä parasta kuvaa!
"""

BTN_ON_PREMISES = "Agora event crop"
BTN_STRAIGHTEN = "Suorista ja rajaa kuva automaattisesti"


THEME_TRANSLATIONS = {
    "adventure": "seikkailu",
    "arcane": "taianomainen",
    "atlantis": "atlantis",
    "augmented_reality_city": "virtuaalinen kaupunki",
    "bazaar": "basaari",
    "carnival": "karnevaali",
    "celestial_bodies": "taivaankappaleet",
    "cyberpunk_future": "kyberpunk tulevaisuus",
    "desert": "aavikko",
    "drawing": "piirros",
    "elves": "haltiat",
    "enhanced_fairytale": "satumaailma",
    "forest": "metsä",
    "garden": "puutarha",
    "hub": "virtuaalinen keskus",
    "ice": "jää",
    "knowledge": "tieto",
    "manor": "kartano",
    "market": "kauppapaikka",
    "mountain": "vuori",
    "myths": "myytti",
    "nature": "luonto",
    "neon": "neon",
    "quantum": "kvantti",
    "robot": "robotti",
    "sanctuary": "kyberneettinen temppeli",
    "steampunk": "steampunk",
    "sunken": "uponnut",
    "travel": "matkustaminen",
    "underground": "maanalainen",
    "utopia": "utopia"
}

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


def add_image_description(img_input, chat_history):
    # Used to add image description to image description box.

    try:
        with open(img_input, "rb") as fd:
            # sha = uuid4()
            sha = hashlib.sha256(fd.read()).hexdigest()
            fname = f"{sha}.jpg"
            target_file = settings.INSTANCE_PATH / "original" / fname
        with open(img_input, "rb") as fd:
            with open(target_file, "wb") as out_file:
                out_file.write(fd.read())

        chat_history += [
            ChatMessage(
                role="assistant",
                content="Tarkastellaan kuvaa... 🧐",
            )
        ]

        yield ui_chatbot(chat_history), "..."

        # if BTN_STRAIGHTEN in options:
        #     autocrop_and_straighten(img_input, target_file)
        # else:
        #     autocrop(img_input, target_file)

        yield ui_chatbot(chat_history),  "..."

        description = get_sketch_description(fname)
        # description = "ASDF"

        # chat_history += [
        #     ChatMessage(
        #         role="assistant",
        #         content="""
        #         Kuvan tarkastelu valmis! 🤗
        #         Valitse seuraavaksi kuvallesi teema, ja muokkaa halutessasi tekoälyn käsitystä kuvasi sisällöstä.
        #         Kun olet valmis, klikkaa "Generoi", niin tekoäly piirtää kuvasi uudelleen 🦾🤖
        #         """,
        #     )
        # ]

        chat_history += [
            ChatMessage(
                role="assistant",
                content="""
                Kuvan tarkastelu valmis! 🤗
                """,
            )
        ]

        yield ui_chatbot(chat_history), description

    except Exception as e:
        chat_history += [
            ChatMessage(
                role="assistant",
                content=f"Kuvaa käsiteltäessä tapahtui virhe: {e}",
            )
        ]
        gr.Error("An error occurred while processing the image.")
        yield ui_chatbot(chat_history), ""
        return 
    

def generate_image(chat_history, img_input, prompt, theme):
    # Generates the image from description, theme and image.
    # TODO: Omaan välilehteen aukaisu linkki tyyliin:
    # http://localhost:8000/original_images/736e8f71bbc77c197ee4d02cb790e1710975c73623c134d9e0098a8038a7cf1e.jpg
    try:
        with open(img_input, "rb") as fd:
            # sha = uuid4()
            sha = hashlib.sha256(fd.read()).hexdigest() 
            fname = f"{sha}.jpg"
            target_file = settings.INSTANCE_PATH / "original" / fname

        # Default to drawing if no theme is selected
        # TODO: should it be random theme instead?
        if theme is None:
            theme = "ei_teemaa"

        chat_history += [
            ChatMessage(
                role="assistant",
                content=f"Generoidaan kuvaa ⚙️ ..."
            )
        ]

        generative_prompt = generate_themed_prompt(theme, prompt)
        
        positive = generative_prompt["prompt"]
        negative = generative_prompt["negative_prompt"]
        
        # chat_history += [ChatMessage(
        #         role="assistant",
        #         content=f"Generating image with theme {theme!r} and using the following promt:\n\n{positive!r}\n\n{negative!r}"
        #     )]
    
        yield ui_chatbot(chat_history)

        img2img = image_to_image(fname, positive, negative)
    
        chat_history += [ChatMessage(
            role="user",
            content=img2img['output_filename']
        )]

        yield ui_chatbot(chat_history)

        # chat_history += [
        #     ChatMessage(
        #         role="assistant",
        #         content=gr.Image(value=str(target_file))
        #     ),
        #     ChatMessage(
        #         role="assistant",
        #         content=prompt
        #     )
        # ]

        chat_history += [ChatMessage(
            role="user",
            content="**Voting**: You can [now go and vote for your favorite – or own – AI-patched image!](https://itk-pj-voting.byteboat.fi/)\n![](https://itk-pj-voting.byteboat.fi/static/voting_qr.png)"
        )]

        yield ui_chatbot(chat_history)
        
    except Exception as e:
        chat_history += [
            ChatMessage(
                role="assistant",
                content=f"Kuvaa käsiteltäessä tapahtui virhe: {e}",
            )
        ]
        gr.Error("An error occurred while processing the image.")
        yield ui_chatbot(chat_history)
        return 

 




    # gr.Info("ℹ️ Image has been created! Go vote!", duration=10)
    # return 


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

        # chat_history += [
        #     ChatMessage(
        #         role="assistant",
        #         content="Do you wish to provide an email address to participate in the contest?"
        #     )
        # ]
        # if email:
        #     chat_history += [
        #         ChatMessage(
        #             role="user",
        #             content="✅ Sure!"
        #         )
        #     ]
        #     save_email(fname, email)
        # else:
        #     chat_history += [
        #         ChatMessage(
        #             role="user",
        #             content="⛔ No thanks."
        #         )
        #     ]

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

    # Break from here

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

    custom_css = """
        #image-upload {
            flex-grow: 1;
        }
        #params .tabs {
            display: flex;
            flex-direction: column;
            flex-grow: 1;
        }
        #params .tabitem[style="display: block;"] {
            flex-grow: 1;
            display: flex !important;
        }
        #params .gap {
            flex-grow: 1;
        }
        #params .form {
            flex-grow: 1 !important;
        }
        #params .form > :last-child{
            flex-grow: 1;
        }
    """
    
    custom_js = """
    function wrap() {
        var outerDiv = document.querySelector('[title="grant webcam access"]');
        console.log(outerDiv);
        var innerDiv = outerDiv.querySelector(".wrap.svelte-qbrfs");
        console.log(innerDiv);
        innerDiv.childNodes.forEach(node => {
        if (node.nodeType === Node.TEXT_NODE) {
            if (node.textContent.trim()) {
                node.textContent = 'Klikkaa tästä käyttääksesi kameraa';
            }
        }
        });
    }
    """

    with gr.Blocks(fill_height=True, title="Tutkijoiden yö 📸", css=custom_css, js = custom_js) as app:

        with gr.Row(equal_height=True):
            
            with gr.Column():
                img_input = gr.Image(
                    height=400,
                    type="filepath",
                    sources=["webcam", "upload"],
                    label="Lataa kuva",
                    mirror_webcam=False,
                    show_label=False,
                    elem_id="image-upload"
                )

            with gr.Column(elem_id="params"):
                
                # TODO: Should themes be enabled
                themes = get_image_themes()
                # Always include the "drawing" as the first option
                # choices_en = random.sample(themes, 5)
                
                # # if "drawing" in choices_en:
                # #     themes.remove("drawing")
                # # choices_en.insert(0, "drawing")
                # choices_en = themes
                # choices = []

                # for choice in choices_en:
                #     if choice in THEME_TRANSLATIONS:
                #         choices.append((THEME_TRANSLATIONS[choice], choice))
                #     else:
                #         choices.append((choice, choice))

                theme = gr.Dropdown(
                    choices=themes,
                    label="Valitse kuvan teema",
                    show_label=True,
                    allow_custom_value=False
                )

                prompt = gr.Textbox(
                    label="Tekoälyn käsitys kuvasi sisällöstä, muokkaa jos olet eri mieltä. Kun olet valmis, klikkaa 'Generoi!'-nappia.", 
                    placeholder="Odotetaan kuvaa...",
                    lines=10,
                    max_lines=10
                )

                # options = gr.CheckboxGroup(
                #     [BTN_STRAIGHTEN],
                #     value=[],
                #     label="Muita valintoja",
                #     show_label=True,
                # )

                generate = gr.Button("Generoi! 🤖")

        # with gr.Row():
            # submit = gr.Button("Submit")
        with gr.Row():
            chatbot = ui_chatbot()

        img_input.input(add_image_description, inputs=[img_input, chatbot], outputs=[chatbot, prompt])
        generate.click(generate_image, inputs=[chatbot, img_input, prompt, theme], outputs=[chatbot])
        # submit.click(process, inputs=[chatbot, img_input, options, theme, prompt], outputs=[chatbot, img_input])
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    app = gra_chatapp()
    app.launch(show_api=False, share=False)
