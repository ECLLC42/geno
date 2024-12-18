from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def generate_lyrics(lyrics):
    try:
        # Construct the prompt
        prompt = f"""Take this sentence: "{lyrics}" 
        and transform it into song lyrics with 2 verses and 1 chorus and 1 outros. 
        Format the output as "[Verse 1]: (content)", "[Chorus]: (content)", "[Verse 2]: (content)", "[Outro]: (content)" Do NOT output in markdown '*', '**', '#', etc. DO NOT do that"""

        # Make the API call
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a songwriter who can turn ideas into meaningful lyrics."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=325,
            temperature=1.0
        )

        # Extract and return the generated lyrics
        return response.choices[0].message.content

    except Exception as e:
        return f"Error generating lyrics: {str(e)}"