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

def advertetise_skill():
    skills = ["Available skills:"]
    
    # Check if the directory exists first to avoid crashes on other tests
    if not os.path.exists(".claude/skills"):
        return ""

    for file_name in os.listdir(".claude/skills"):
        skill_path = f".claude/skills/{file_name}/SKILL.md"
        if not os.path.isfile(skill_path):
            continue
            
        with open(skill_path) as file_:
            name = ""
            description = ""
            
            for line in file_:
                line = line.strip()
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip()

                elif line.startswith("description:"):
                    description = line.split(":", 1)[1].strip()

                elif line == "---" and name and description:
                    break
            
            if name and description:
                skills.append(f"- {name}: {description}")

    return "\n".join(skills)


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

def parse(string: str) -> str:
    words = string.split()
    skills_name = []
    arguments = {}
    
    arg_idx = 0
    for word in words:
        if word.startswith("/"):
            skills_name.append(word[1:])
        else:
            arguments[arg_idx] = word
            arg_idx += 1

    if not skills_name:
        return string

    final_list = []
    for name in skills_name:
        final_list.append(f"Skill: {name} (located at .claude/skills/{name})\nPaths in the instructions below are relative to that folder.")
        final_list.append(get_skill_description(name, arguments))

    return "\n\n".join(final_list) 


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
    if message == args.p:
        message = message + "\n" + advertetise_skill()

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