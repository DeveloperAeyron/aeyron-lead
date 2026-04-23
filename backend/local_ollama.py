# import ollama

# stream = ollama.chat(
#     model="qwen3.5:9b",
#     messages=[{"role": "user", "content": "hi"}],
#     stream=True
# )

# for chunk in stream:
#     print(chunk["message"]["content"], end="", flush=True)



from ollama import chat

response = chat(
  model="qwen3.5:9b",
  messages=[{'role': 'user', 'content': 'hi.'}]
)
print(response.message.content)