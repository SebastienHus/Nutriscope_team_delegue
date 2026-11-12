import base64
import time
from pathlib import Path

from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

# 1 et 2 : le fichier devient du texte base64
photo = Path("../data/photos/10_3608580065340_etiquette.jpg")
image_b64 = base64.b64encode(photo.read_bytes()).decode("ascii")

# 3 : l'adresse data: (le type doit correspondre au format du fichier)
url_image = f"data:image/jpeg;base64,{image_b64}"

# 4 : un message en deux morceaux, texte puis image
messages = [{"role": "user", "content": [
    {"type": "text", "text": "Recopie le tableau nutritionnel de cette photo."},
    {"type": "image_url", "image_url": {"url": url_image}},
]}]

debut = time.perf_counter()
reponse = client.chat.completions.create(
    model="qwen3-vl:8b-instruct", messages=messages, temperature=0
)
print(reponse.choices[0].message.content)
print(f"{time.perf_counter() - debut:.1f} s,",
      reponse.usage.prompt_tokens, "tokens en entrée,",
      reponse.usage.completion_tokens, "en sortie")