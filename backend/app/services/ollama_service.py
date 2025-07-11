import ollama

class OllamaService:
    def __init__(self, model_name="mistral:7b-instruct-v0.3-fp16"):
        self.model_name = model_name

    def generate_faq_batch(self, text_chunk, num_faqs_per_chunk):
        prompt = f"""
        Generate exactly {num_faqs_per_chunk} FAQ questions and answers based on the following text.
        Format each FAQ strictly as: "Q: question here\nA: answer here\n\n"
        Text: {text_chunk}
        """
        try:
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                options={'temperature': 0.2, 'num_predict': 300}
            )
            return response['response']
        except Exception as e:
            print(f"Error generating FAQ batch with Ollama: {e}")
            return None

    def check_ollama_status(self):
        try:
            ollama.list()
            return True
        except:
            return False
