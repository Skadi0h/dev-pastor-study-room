import dataclasses

from transformers import AutoTokenizer, AutoModelForCausalLM

from config import CONFIG


@dataclasses.dataclass(slots=True)
class GemmaService:
    tokenizer = AutoTokenizer.from_pretrained("google/gemma-2b-it", token=CONFIG.hf_token)
    model = AutoModelForCausalLM.from_pretrained("google/gemma-2b-it", device_map="auto", token=CONFIG.hf_token)

    def get_answer(self, message: str) -> str:
        input_ids = self.tokenizer(message, return_tensors="pt").to("cuda")

        outputs = self.model.generate(**input_ids)
        return self.tokenizer.decode(outputs[0])

