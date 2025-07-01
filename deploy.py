from fastapi import FastAPI
from pydantic import BaseModel
import requests
import time
import os 
from dotenv import load_dotenv



# Load variables from .env file into environment
load_dotenv()

# Access variables

api_key = os.getenv("API_KEY")
endpoint = os.getenv("API_ENDPOINT")

app = FastAPI()

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
         "أنت فقيه متخصص في الدين الإسلامي، تجيب عن الأسئلة المتعلقة بالحج والعمرة بلغة واضحة وبأسلوب رحيم، "
        "مستندًا إلى الأدلة الشرعية من القرآن الكريم والسنة النبوية. تحدث بلغة السائل (العربية أو الإنجليزية)، "
        "ولا تُصدر فتاوى شخصية، بل تُرشد السائل إلى مصادر موثوقة أو تطلب منه مراجعة أهل العلم عند الضرورة."
    )
}



# session memory 
session_memories = {}

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    session_id: str
    messages: list[Message]
    reset_session: bool = False  


@app.post("/chat")
def chat_endpoint(chat_request: ChatRequest):
    session_id = chat_request.session_id

    if chat_request.reset_session or session_id not in session_memories:
        session_memories[session_id] = [{"role": "system", "content": SYSTEM_PROMPT["content"]}]  # إرسال SYSTEM_PROMPT في أول مرة فقط

    for msg in chat_request.messages:
        session_memories[session_id].append(msg.dict())

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    data = {
        "model": "gpt-3.5-turbo",  
        "messages": session_memories[session_id],  
        "temperature": 0.0,
        "max_tokens": 350  # specify tokens 
    }

    retries = 5
    for attempt in range(retries):
        response = requests.post(endpoint, headers=headers, json=data)

        if response.status_code == 200:
            reply = response.json()["choices"][0]["message"]["content"]
            session_memories[session_id].append({"role": "assistant", "content": reply}) # saving response in memory
            print("✅ Reply received.")
            return {
                "response": reply
            }

        elif response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 2 ** attempt))
            time.sleep(retry_after)

        else:
            return {
                "error": f"{response.status_code}: {response.text}"
            }

    return {
        "error": "The service is currently busy. Please try again later."
    }