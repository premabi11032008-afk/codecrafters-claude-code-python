import argparse
import os
import sys
import inspect
from . import tools
import json
import re

from openai import OpenAI

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")
REGRESS_EXP = r"\$ARGUMENTS\[\d+\]|\$ARGUMENTS|\$\d+"

def get_tool_registery(module):
    available = {}

    for name, function in inspect.getmembers(module, inspect.isfunction):
        available[name] = function

    return available

def get_skill_description(skill_name, arguments):
    with open(f".claude/skills/{skill_name}/SKILL.md") as file:
        content = file.readlines()

    def replacement_func(match):
        args : dict = arguments
        match_ : str = match.group(0)

        if match_[1 : ].isdigit():
            return args.get(int(match_[ 1 : ]), "")

        elif match_ == '$ARGUMENTS':
            return " ".join(args.values())

        else:
            return args.get(int(match_[len('$ARGUMENTS') + 2: -1]), "")
        
    content = "\n".join(content[4 : ])
    content = re.sub(REGRESS_EXP, replacement_func, content)
    return content

def parse(string : str) -> str:

    for idx, word in enumerate(words := string.split()):
        if word[0] == "/" : 
            arguments = { idx_ - idx - 1 : words[idx_] for idx_ in range(idx + 1, len(words))}
            words[idx] = get_skill_description(word[1:], arguments)
            break

    return " ".join(words)


tool_registery = get_tool_registery(tools)

def tool_call(tool_calls):
    responses = []
    for tool in tool_calls:
        function_ = tool.function
        if function_.name in tool_registery:
            args = json.loads(function_.arguments)
            response = tool_registery.get(function_.name)(**args)
            
            responses.append({
                "tool_call_id": tool.id,
                "role": "tool",
                "name": function_.name,
                "content": str(response)
            })
        else:
            responses.append({
                "tool_call_id": tool.id,
                "role": "tool",
                "name": function_.name,
                "content": "Function NOT found"
            })
            
    return responses 



tools_ = [
    {
  "type": "function",
  "function": {
    "name": "Read",
    "description": "Read and return the contents of a file",
    "parameters": {
      "type": "object",
      "properties": {
        "file_path": {
          "type": "string",
          "description": "The path to the file to read"
        }
      },
      "required": ["file_path"]
    }
  }
},
{
  "type": "function",
  "function": {
    "name": "Write",
    "description": "Write content to a file",
    "parameters": {
      "type": "object",
      "required": ["file_path", "content"],
      "properties": {
        "file_path": {
          "type": "string",
          "description": "The path of the file to write to"
        },
        "content": {
          "type": "string",
          "description": "The content to write to the file"
        }
      }
    }
  }
},
{
  "type": "function",
  "function": {
    "name": "Bash",
    "description": "Execute a shell command",
    "parameters": {
      "type": "object",
      "required": ["command"],
      "properties": {
        "command": {
          "type": "string",
          "description": "The command to execute"
        }
      }
    }
  }
}
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    message = parse(args.p)

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    messages = [{"role": "user", "content": message}]
    print("Logs from your program will appear here!", file=sys.stderr)

    while True:

        chat = client.chat.completions.create(
            model="anthropic/claude-haiku-4.5",
            messages=messages,
            tools = tools_
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("no choices in response")

        if array := chat.choices[0].message.tool_calls:
            messages.append(chat.choices[0].message)

            responses = tool_call(array)
            messages.extend(responses)

        else:
            print(chat.choices[0].message.content)
            break


if __name__ == "__main__":
    main()