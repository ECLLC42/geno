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
        and transform it into song lyrics with 2 verses and 1 chorus. 
        Format the output with clear labels for Verse 1, Chorus, and Verse 2.
        Make it emotional and meaningful while keeping the original sentiment of the input."""

        # Make the API call
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a creative songwriter who can turn ideas into meaningful lyrics. Your max token count is 200"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=250,
            temperature=0.9
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