import os
import traceback
from google import genai
from google.genai import types
from dotenv import load_dotenv

def generate_trivia_xml():
    # Ensure your Gemini API key is set as an environment variable
    # e.g., export GEMINI_API_KEY="your_api_key_here"
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("Please set the GEMINI_API_KEY environment variable.")

    # Configure the Gemini API client
    client = genai.Client(api_key=api_key)

    # Instantiate the model (using gemini-1.5-flash as it is fast and excellent for text/XML generation tasks)
    #model = genai.GenerativeModel('gemini-1.5-flash')

    # The original XML structure provided, used as a structural reference
    reference_xml = """
    <game>
        <category name="Pop Culture">
            <entry value="200">
                <question>This artist has the most streams on Spotify.</question>
                <answer>Taylor Swift</answer>
            </entry>
            </category>
    </game>
    """
    
    # Formulate the prompt instructing the model to generate similar XML
    prompt = f"""
    You are an expert trivia writer and XML data formatter.
    
    Here is a sample of the desired XML structure for a trivia game:
    {reference_xml}
    
    Generate a complete, new XML file following this exact same schema. 
    Requirements:
    1. Create 5 completely new and distinct categories (e.g., 'World History', 'Science & Nature', 'Sports', 'Literature', 'Video Games').
    2. Provide exactly 5 entries per category.
    3. The entry values must strictly be 200, 400, 600, 800, and 1000 in order for each category.
    4. Provide a unique <question> and <answer> for each entry that matches the difficulty of the value.
    5. Output ONLY valid XML. Do not include markdown formatting like ```xml or any conversational text.
    6. Wrap the entry XML outout in '<game>' tag.
    """

    # Generate the content
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents = prompt,
            config=types.GenerateContentConfig(
                temperature=0.1, # A slight amount of creativity for fun trivia categories
            )
        )
        
       # Clean markdown backticks just in case the model includes them
        clean_result = response.text.replace('```xml', '').replace('```', '').strip()

        # Output the generated XML
        #with open("testOutput.txt", "w", encoding="utf-8") as f:
        #    f.write("=== SUCCESS ===\n")
        #    f.write(clean_result)
            
        return clean_result
        
    except Exception as e:
        # Capture the full traceback and force it into the text file
        error_trace = traceback.format_exc()
        
        with open("testOutput.txt", "w", encoding="utf-8") as f:
            f.write("=== ERROR ===\n")
            f.write(str(e) + "\n\n")
            f.write(error_trace)
            
        print(f"An error occurred: {e}")
        return None


if __name__ == "__main__":
    generate_more_trivia_xml()
