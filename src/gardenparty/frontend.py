"""
Gradio frontend
"""
import gradio as gr
import os

from gardenparty.preprocess import autocrop_and_straighten, save_image_as

from uuid import uuid4

from gardenparty.app import settings

# Disable telemetry

os.environ.setdefault("GRADIO_TELEMETRY", "0")
os.environ.setdefault("GRADIO_SERVER_NAME", "0.0.0.0")

DESCRIPTION = r"""
## IT-Faculty Garden Party 2024: The AI patcher

1. Acquire an image using the camer or upload an image
2. (Optional) Fill in your email address to participate in the contest
3. Let the AI patcher do its magic
4. Vote for the best AI-patched image
"""

def acquire(img_input, auto_adjust=True):

    # Generate a random UUID for the output file
    target_file = f"{settings.original_images_dir}/{uuid4()}.webp"

    if auto_adjust:
        autocrop_and_straighten(img_input, target_file)
    else:
        save_image_as(img_input, target_file)

    return gr.Image(target_file, type="filepath", interactive=False)

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

if __name__ == "__main__":
    app.queue().launch()
