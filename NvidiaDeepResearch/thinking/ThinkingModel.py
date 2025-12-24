from openai import OpenAI
import os, getpass

from dotenv import load_dotenv

load_dotenv(dotenv_path="my.env")


# TURN OFF ZSCALER
client = OpenAI(
  base_url = "https://integrate.api.nvidia.com/v1",  # NVIDIA endpoint
  api_key = os.environ["NGC_API_KEY"]                # Your API key
)

model_failed = "nvidia/llama-3.3-nemotron-super-49b-v1"
model = "nvidia/llama-3.3-nemotron-super-49b-v1.5"
model_small = "nvidia/nvidia-nemotron-nano-9b-v2"

# Parameter	Value	Purpose
# messages[0]	"/think"	Activates reasoning mode - tells the model to show its thinking process
# temperature	0.6	Moderate creativity (higher = more creative, lower = more focused)
# top_p	0.95	Considers top 95% probability tokens (nucleus sampling)
# max_tokens	65536	Allows very long responses (important for reasoning, which can be verbose)
# stream	True	Returns response incrementally, like ChatGPT's typing effect
#


# #nvidia/llama-3.3-nemotron-super-49b-v1.5
completion_reasoning = client.chat.completions.create(

  model=model,
  messages=[
    {"role":"system", "content":"/think"},  # Standard system message
    {"role":"user", "content":"How many 'r's are in 'strawberry'?"}
  ],
  temperature=0.6,
  top_p=0.95,
  max_tokens=1024,
  stream=True
)
print("\n response WITH reasoning:\n")
for chunk in completion_reasoning:
  if chunk.choices[0].delta.content is not None:
    print(chunk.choices[0].delta.content, end="")



completion_no_reasoning = client.chat.completions.create(

  model=model,
  messages=[
    {"role":"system", "content":"/no_think"},  # Standard system message
    {"role":"user", "content":"How many 'r's are in 'strawberry'?"}
  ],
  temperature=0.6,
  top_p=0.95,
  max_tokens=1024,
  stream=True
)
print("\n response WITHOUT reasoning:\n")
for chunk in completion_no_reasoning:
  if chunk.choices[0].delta.content is not None:
    print(chunk.choices[0].delta.content, end="")