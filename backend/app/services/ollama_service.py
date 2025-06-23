import requests
import json

class OllamaService:
    def __init__(self, ollama_base_url="http://localhost:11434"):
        self.ollama_base_url = ollama_base_url

    def generate_qa_from_text(self, text):
        print("generate_qa_from_text:", text)  # Add this line
        prompt = f"""Given the following text, extract 10 distinct questions and their corresponding answers. Format the output as a JSON array of objects, where each object has 'question' and 'answer' keys. Ensure the questions and answers are directly derivable from the text provided.

Text: {text}

JSON Output:"""
        
        payload = {
            "model": "mistral:7b-instruct-v0.3-fp16",
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(f"{self.ollama_base_url}/api/generate", json=payload)
            response.raise_for_status()  # Raise an exception for HTTP errors
            
            response_data = response.json()
            generated_text = response_data.get("response", "")
            
            # Attempt to parse the generated text as JSON
            try:
                qa_pairs = json.loads(generated_text)
                print("Generated QA Pairs:", qa_pairs)
                if not isinstance(qa_pairs, list):
                    raise ValueError("Expected a JSON array.")
                return qa_pairs
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from Ollama response: {generated_text}")
                return []

        except requests.exceptions.RequestException as e:
            print(f"Error communicating with Ollama: {e}")
            return []

    def parse_ollama_response(self, response_text):
        # This method might be used if the direct JSON parsing in generate_qa_from_text isn't sufficient
        # For now, generate_qa_from_text attempts direct JSON parsing.
        try:
            qa_pairs = json.loads(response_text)
            if not isinstance(qa_pairs, list):
                raise ValueError("Expected a JSON array.")
            return qa_pairs
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from Ollama response: {response_text}")
            return []
