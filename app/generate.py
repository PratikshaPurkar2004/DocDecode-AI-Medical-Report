import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

CHAT_MODEL = os.getenv(
    "GEMINI_CHAT_MODEL",
    "gemini-3.5-flash-lite"
)


def generate_text(
    system_prompt: str,
    user_prompt: str,
    history_messages: list[dict] | None = None
) -> str:

    """
    Generate a response using the Gemini API.
    """

    contents = []

    if history_messages:
        for msg in history_messages:

            role = (
                "model"
                if msg["role"] in ("assistant", "model")
                else "user"
            )

            contents.append(
                types.Content(
                    role=role,
                    parts=[
                        types.Part(text=msg["content"])
                    ]
                )
            )

    contents.append(
        types.Content(
            role="user",
            parts=[
                types.Part(text=user_prompt)
            ]
        )
    )

    # Retry temporary 503 errors
    for attempt in range(3):

        try:

            resp = client.models.generate_content(
                model=CHAT_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                ),
            )

            return resp.text.strip()

        except Exception as e:

            error_text = str(e)

            if "503" in error_text or "UNAVAILABLE" in error_text:

                if attempt < 2:

                    wait_time = 2 ** attempt

                    print(
                        f"Gemini temporarily unavailable. "
                        f"Retrying in {wait_time} seconds..."
                    )

                    time.sleep(wait_time)

                else:

                    return (
                        "The AI service is temporarily busy. "
                        "Please try again in a few moments."
                    )

            else:
                raise