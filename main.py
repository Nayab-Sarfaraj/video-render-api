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
from supabase import create_client, Client

load_dotenv()
app=FastAPI()



# Set your Supabase URL and API KEY (Service Role key preferred for file uploads)
print(os.getenv("SUPABASE_URL"))
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_API_KEY)



# cred = credentials.Certificate("serviceAccountKey.json")
# firebase_admin.initialize_app(cred, {
#     'storageBucket': 'chat-to-myself.appspot.com'
# })



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
def render_video(data: schemas.request):
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

        file_name = f"{uuid.uuid4().hex}.mp4"
        storage_path = f"videos/{file_name}"
        with open(OUTPUT_VIDEO, "rb") as video_file:
            contents = video_file.read()

        response = supabase.storage.from_(SUPABASE_BUCKET).upload(
            path=storage_path,
            file=contents,
            file_options={"content-type": "video/mp4"}
        )

        # Optional: Make it "public" by getting its public URL
        public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(storage_path)

        # 👇 Return the video URL
        return {"status": "done", "video_url": public_url}

    except Exception as e:
        return {"error": str(e)}

    finally:
        for f in image_paths + [audio_path]:
            os.remove(f)
