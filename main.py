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

load_dotenv()
app=FastAPI()
print(os.getenv("firebase_json"))



cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'bookify-8084d.appspot.com'
})



def download_file(url, filename):
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






@app.post("/render")
def render_video(data:schemas.request):
    try:
        image_paths = [download_and_resize_image(url) for url in data.images]

        print("Downloading audio files...")
        audio_path = download_file(data.story_audio, "test.mp3")

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

        # ✅ Upload to Firebase Storage
        bucket = storage.bucket()
        blob = bucket.blob(f"{uuid.uuid4().hex}.mp4")
        with open(OUTPUT_VIDEO, "rb") as video_file:
            blob.upload_from_file(video_file, content_type="video/mp4")
        blob.make_public()  # Optional, makes it publicly accessible

        # 👇 Return the video URL
        return {"status": "done", "video_url": blob.public_url}


    except Exception as e:
        return {"error": str(e)}
    finally:
        for f in image_paths + [audio_path ]:
                     os.remove(f)