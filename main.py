from fastapi import FastAPI
from moviepy import ImageClip, concatenate_videoclips, AudioFileClip, TextClip, CompositeVideoClip, vfx
import requests
import os
from PIL import Image
from io import BytesIO
import uuid
from dotenv import load_dotenv,dotenv_values
from fastapi import FastAPI, UploadFile, File
import firebase_admin
from firebase_admin import credentials, storage
import schemas
import os
import inngest
import inngest.fast_api
import logging
from fastapi.encoders import jsonable_encoder

load_dotenv()


app=FastAPI()

print(os.getenv("INNGEST_SIGNING_KEY "))
print(os.getenv("INNGEST_EVENT_KEY "))


# Create an Inngest client
inngest_client = inngest.Inngest(
    app_id="fast_api_example",
    logger=logging.getLogger("uvicorn"),
    signing_key=os.getenv("INNGEST_SIGNING_KEY"),
    event_key=os.getenv("INNGEST_EVENT_KEY")
)

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'bookify-8084d.appspot.com'
})



def download_audio(url, filename):
    r = requests.get(url)
    with open(filename, 'wb') as f:
        f.write(r.content)
    return filename


def download_and_resize_image(url):
    response = requests.get(url)
    img = Image.open(BytesIO(response.content)).convert("RGB")
    path = f"temp_{hash(url)}.jpg"
    img.save(path)
    return path


def upload_to_firebase(video_path):
    print("Uploading on the firebase..............")
    # bucket = storage.bucket()
        # blob = bucket.blob(f"{uuid.uuid4().hex}.mp4")
        # with open(OUTPUT_VIDEO, "rb") as video_file:
            # blob.upload_from_file(video_file, content_type="video/mp4")
        # blob.make_public()  # Optional, makes it publicly accessible
    bucket = storage.bucket()
    blob = bucket.blob(f"{uuid.uuid4().hex}.mp4")
    with open(video_path, "rb") as video_file:
        blob.upload_from_file(video_file, content_type="video/mp4")
    blob.make_public()
    return blob.public_url


def cleanup(paths):
    print("Cleaning up..........")
    for f in paths:
        if os.path.exists(f):
            os.remove(f)

def download_images_step(image_urls):
    print("Downloading Images.........")
    return [download_and_resize_image(url) for url in image_urls]

def download_audio_step(url):
    print("Downloading videos.........")
    return download_audio(url, "temp_audio.mp3")

def resize_function(t):
    return 1 + 0.05 * t


def render_video(payload):        
    image_paths = payload["images"]
    audio_path = payload["audio"]

    audio = AudioFileClip(audio_path)

    clips = []

    for path in image_paths:
        clip = (
                ImageClip(path)
                .with_duration(audio.duration / len(image_paths))
                .resized(height=720)
                .resized(lambda t: 1 + 0.05 * t)
                .with_position("center")
            )
        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")
    video = video.with_audio(audio)

    OUTPUT_VIDEO = "output.mp4"
    video.write_videofile(OUTPUT_VIDEO, fps=24)
    return OUTPUT_VIDEO


@inngest_client.create_function(
    fn_id="generate-youtube-short",
    trigger=inngest.TriggerEvent(event="generate-youtube-short"),
)
async def generate_video(ctx: inngest.Context, step: inngest.Step):
    data = ctx.event.data
    try:
        image_paths = await step.run("download-images", download_images_step, data["images"])
        audio_path = await step.run("download-audio", download_audio_step, data["story_audio"])
        video_path = await step.run("render-video", render_video, {
            "images": image_paths,
            "audio": audio_path
        })
        video_url = await step.run("upload-video", upload_to_firebase, video_path)

        await step.run("cleanup", cleanup, image_paths + [audio_path, video_path])

        return { "status": "done", "video_url": video_url }
    except Exception as e:
        return { "error": str(e) }



inngest.fast_api.serve(app, inngest_client, [generate_video])


@app.post("/render")
def render(data:schemas.request):
    request = jsonable_encoder(data)  # Convert to plain dict

    ids=inngest_client.send_sync(
    inngest.Event(name="generate-youtube-short", data=request))
    return ids


