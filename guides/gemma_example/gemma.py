from dotenv import dotenv_values
from transformers import AutoTokenizer, AutoModelForCausalLM

config = dotenv_values(".env")


tokenizer = AutoTokenizer.from_pretrained("google/gemma-2b-it", token=config["HF_TOKEN"])
model = AutoModelForCausalLM.from_pretrained("google/gemma-2b-it", device_map="auto", token=config["HF_TOKEN"])

input_text = "How are you?"
input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

outputs = model.generate(**input_ids)
print(tokenizer.decode(outputs[0]))