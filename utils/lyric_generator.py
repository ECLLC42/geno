from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def generate_lyrics(input_sentence):
    try:
        # Construct the prompt
        prompt = f"""Take this sentence: "{input_sentence}" 
        and transform it into song lyrics with 2 verses and 1 chorus and 1 outros. 
        Format the output as Verse 1: (content), Chorus: (content), Verse 2: (content), Chorus: (chorus content)Outro: (content). Do NOT output in markdown '*', '**', '#', etc. DO NOT do that"""

        # Make the API call
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a songwriter for children's songs who can turn ideas into meaningful lyrics. Your max token count is 500"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=1.0
        )

        # Extract and return the generated lyrics
        return response.choices[0].message.content

    except Exception as e:
        return f"Error generating lyrics: {str(e)}"

# Example usage
if __name__ == "__main__":
    test_input = "The sun sets over the ocean"
    lyrics = generate_lyrics(test_input)
    print(lyrics) 