import argparse
import os
import sys
import inspect
from . import tools, lsp_client
import json
import re
from .tool_list import tools_
from .utils import uri_to_path

from openai import OpenAI

lsp_client_ = lsp_client.LSPClient.from_environment()
tools.client = lsp_client_
cursor = 0

def formate_notification(notifications: list):
    file_refrences = {}
    for notification in notifications:
        params = notification.get("params", {})
        version = params.get("version")
        uri = params.get("uri")

        if version is not None and tools.opened_uris.get(uri, 1) != version:
            continue

        path = uri_to_path(uri) 

        diagnostics_list = params.get("diagnostics", [])
        file_refrences[path] = [] 

        for diag in diagnostics_list:
            start = diag.get("range", {}).get("start", {})

            line_ = start.get("line", 0) + 1
            char_ = start.get("character", 0) + 1
            message = diag.get("message", "")
            
            file_refrences[path].append(f"   [Line {line_}:{char_}] {message}")

    if file_refrences == {}:
        return ""

    final_string = ["<new-diagnostics>The following new diagnostic issues were detected:\n"]
    for path in file_refrences:
        final_string.append(path)
        final_string.extend(file_refrences[path])
        final_string.append("\n")

    return "\n".join(final_string[:-1]) + "</new-diagnostics>"



def advertetise_skill():
    skills = ["Available skills:"]
    
    if not os.path.exists(".claude/skills"):
        return ""

    for file_name in os.listdir(".claude/skills"):
        skill_path = f".claude/skills/{file_name}/SKILL.md"
        if not os.path.isfile(skill_path):
            continue
        fork = False
            
        with open(skill_path) as file_:
            name = ""
            description = ""
            val = []
            line_encountered = 0
            
            for line in file_:
                line = line.strip()
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip()

                elif line.startswith("description:"):
                    description = line.split(":", 1)[1].strip()

                elif line.startswith("context: fork") and line_encountered <= 1:
                    fork = True

                elif line == "---":
                    line_encountered += 1

                elif name and description:
                    val.append(line)
                    
            
            if name and description:
                skills.append(f"- {name}: {description}")
                SKILLS[name] = {"content" : "\n".join(val), "is_forked" : fork}

    return "\n".join(skills)


def get_tool_registery(module):
    available = {}

    for name, function in inspect.getmembers(module, inspect.isfunction):
        available[name] = function

    return available

def Skill(name, args = None, client = None):

    if args is None:
        args = {}

    if name not in SKILLS:
        return "SKILL Name Does Not  Exits"

    def replacement_func(match):
        args_ : dict = args
        match_ : str = match.group(0)

        if match_[1 : ].isdigit():
            return args_.get(int(match_[ 1 : ]), "")

        elif match_ == '$ARGUMENTS':
            return " ".join(args_.values())

        else:
            return args_.get(int(match_[len('$ARGUMENTS') + 2: -1]), "")
        
    skill_ = SKILLS.get(name)
    content = re.sub(REGRESS_EXP, replacement_func, skill_["content"])

    if skill_["is_forked"]:
        message = [{"role": "user", "content": content}]
        response = run_agent(client, message)
        return f"Skill {name} ran in a separate context and returned: {response}"

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
        final_list.append(f"The skill {name} is located at .claude/skills/{name}\nPaths in the instructions below are relative to that folder.")
        final_list.append(Skill(name, arguments))

    return "\n\n".join(final_list) 


tool_registery = get_tool_registery(tools)
tool_registery["Skill"] = Skill

def tool_call(tool_calls, client):
    responses = []
    for tool in tool_calls:
        function_ = tool.function
        if function_.name in tool_registery:
            args = json.loads(function_.arguments)

            if function_.name == "Skill":
                response = tool_registery.get(function_.name)(**args, client=client)
            else:
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

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")
REGRESS_EXP = r"\$ARGUMENTS\[\d+\]|\$ARGUMENTS|\$\d+"
SKILLS = {}
skills_list = advertetise_skill()


def run_agent(client, messages, tools = tools_):
    global cursor

    while True:
    
        chat = client.chat.completions.create(
            model="anthropic/claude-haiku-4.5",
            messages=messages,
            tools = tools
        )
    
        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("no choices in response")
    
        if array := chat.choices[0].message.tool_calls:
            messages.append(chat.choices[0].message)
    
            responses = tool_call(array, client)
            messages.extend(responses)

            res = lsp_client_.notifications(after = cursor)
            cursor = res.get("cursor", 0)
            new_messages = res.get("notifications", [])

            formated_notifications = formate_notification(new_messages)
            if formated_notifications != "":
                messages.append(formated_notifications)
        else:
            return chat.choices[0].message.content


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    message = parse(args.p)

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    if message == args.p:
        message = message + "\n" + skills_list

    messages = [{"role": "user", "content": message}]

    print("Logs from your program will appear here!", file=sys.stderr)
    print(run_agent(client, messages))
    


if __name__ == "__main__":
    main()