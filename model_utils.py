import os
from groq import Groq

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

client = Groq(api_key=GROQ_API_KEY)

responses = {
    "joy": "I am happy you are feeling joyful 😊",
    "sad": "I am sorry you are feeling sad 💛",
    "anger": "It is okay to feel angry 🌬️",
    "fear": "You are safe here 💙",
    "neutral": "Thank you for sharing 😊"
}

def detect_emotion(text):
    text = text.lower()
    if any(w in text for w in ["sad","unhappy","cry","upset","depressed","hurt"]):
        return "sad"
    elif any(w in text for w in ["angry","anger","mad","frustrated","hate","annoyed"]):
        return "anger"
    elif any(w in text for w in ["happy","joy","excited","great","good","love","fun","yay"]):
        return "joy"
    elif any(w in text for w in ["scared","fear","afraid","worried","anxious","panic","nervous"]):
        return "fear"
    else:
        return "neutral"

def get_groq_reply(user_input, emotion):
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are FeelBuddy, a warm caring best friend chatbot for autistic children aged 6-14. Talk like a kind friendly buddy. Use very simple easy words. Max 2 short sentences. Use 1-2 emojis. Be warm and gentle. Keep reply under 40 words."
                },
                {
                    "role": "user",
                    "content": f"I feel {emotion}. {user_input}"
                }
            ],
            max_tokens=100,
            temperature=0.8
        )
        reply = response.choices[0].message.content.strip()
        if len(reply) > 200:
            reply = reply[:200]
        return reply
    except Exception as e:
        print(f"Groq error: {e}", flush=True)
        return None

def predict_emotion(user_input):
    prediction = detect_emotion(user_input)
    groq_reply = get_groq_reply(user_input, prediction)
    if groq_reply:
        return prediction, groq_reply
    return prediction, responses.get(prediction, "Thank you for sharing 💛")