from openai import OpenAI
import re
import os
from pathlib import Path

client = OpenAI(base_url="http://localhost:1234/v1", api_key="C-137")

PROYECTO = Path("./workspace").resolve()
PROYECTO.mkdir(exist_ok=True)

PATRON_TOOL = re.compile(r"<tool\s+([^>]*?)>(.*?)</tool>", re.DOTALL)
PATRON_ATTR = re.compile(r'(\w+)="([^"]*)"')

PATRON_TOOL_LFM = None
PATRON_NAME_LFM = None
PATRON_ARGS_LFM = None

try:
    SYSTEM_PROMPT = open("system_prompt.txt", "r", encoding='utf-8').read()
except Exception as e:
    print(e)

historial = [{"role": "system", "content": SYSTEM_PROMPT}]
AUTONOMO = True
MODEL = "lfm2.5-8b-a1b"


def safe_path(path:str) -> Path:
    destino = (PROYECTO / path).resolve()

    if not destino.is_relative_to(PROYECTO):
        raise ValueError("Ruta fuera del proyecto")
    
    return destino

def decode_call(attrs: str, cuerpo: str) -> dict:
    tool = dict(PATRON_ATTR.findall(attrs))

    if cuerpo.startswith("\n"):
        cuerpo = cuerpo[1:]
    if cuerpo.endswith("\n"):
        cuerpo = cuerpo[:-1]

    if cuerpo.startswith("```"):
        cuerpo = cuerpo.split("\n", 1)[1] if "\n" in cuerpo else ""
        cuerpo = cuerpo.rsplit("```", 1)[0].rstrip("\n")

    tool["content"] = cuerpo

    return tool

def decode_call_lfm(tool_struct:str):
    tool_name = PATRON_NAME_LFM.findall(tool_struct)[0]
    tool_args = PATRON_ARGS_LFM.findall(tool_struct)[0].split(",")

    JSON = {"name": tool_name}

    for i in tool_args:
        k, v = i.strip().split("=")
        k = k.replace('"','').replace("'", '')
        v = v.replace('"', '').replace("'", '')
        JSON[k] = v

    return JSON

def ejecutar_tool(tool: dict) -> str:

    name = tool["name"]
    
    try:

        if name == "create_file":
            destino = safe_path(tool["path"])
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(tool.get("content", ""), encoding="utf-8")
            return f"OK: archivo creado en {tool['path']}"
        
        elif name == "read_file":
            return safe_path(tool["path"]).read_text(encoding="utf-8")[:1000]
        
        elif name == "list_directory":
            return f"{os.listdir(safe_path(tool["path"]))}"
        
        elif name == "edit_file":
            with open(safe_path(tool["path"]), "a", encoding="utf-8") as f:
                f.write(f"\n{tool['content']}")
            return f"OK: se escribio en {tool['path']}"

        elif name == "grep":
            text_ = "No se encontro coincidencia"
            with open(safe_path(tool["path"]), "r", encoding='utf-8') as f:
                for numero_linea, linea in enumerate(f,1):
                    if re.search(tool["text"], linea):
                        text_ = f"Linea {numero_linea}: {linea.strip()}"
            return text_
        
        return f"ERROR: herramienta desconocida '{tool}'"
    
    except Exception as e:
        return f"ERROR: {e}"

def send_get_mesg():

    respuesta = client.chat.completions.create(     
            model = MODEL,
            messages = historial,
            stream = True,
            temperature = 0.25,
        )

    fase = None
    texto_completo = ""

    for chunk in respuesta:
        texto = chunk.choices[0].delta.content
        try:
            razonamiento = chunk.choices[0].delta.reasoning_content
        except AttributeError:
            razonamiento = None

        if razonamiento:
            if fase != "razonamiento":
                fase = "razonamiento"
                print("\n","razonamiento:", sep="")
            print(razonamiento, end="", flush=True)

        elif texto:
            if fase != "respuesta":
                fase = "respuesta"
                print("\n\nrespuesta:")
            print(texto, end="", flush=True)
            texto_completo += texto
    return texto_completo


if __name__ == '__main__':

    usar_lfm = input("modo compatible con LFM (y/n): ").lower()

    if usar_lfm == "y":
        PATRON_TOOL_LFM = re.compile(r"<\|tool_call_start\|>\[(.*?)\]<\|tool_call_end\|>")
        PATRON_NAME_LFM = re.compile(r"(.+?)\(")
        PATRON_ARGS_LFM = re.compile(r"\((.+?)\)")

    while True: 

        msg = input("\nTú: ").strip()

        if msg.lower() == "/salir":
            break

        historial.append({"role": "user", "content": msg})

        while True:

            texto_completo = send_get_mesg()

            if texto_completo:
                historial.append({"role": "assistant", "content": texto_completo})
            else:
                historial.pop()

            llamadas_tool = PATRON_TOOL.findall(texto_completo) if usar_lfm == "n" else PATRON_TOOL_LFM.findall(texto_completo)
            resultados_tool = []

            if usar_lfm == "y" and llamadas_tool:
                llamadas_tool = llamadas_tool[0].split("),")

                for i in range(len(llamadas_tool)):
                    llamadas_tool[i] = llamadas_tool[i].strip()
                    if i < len(llamadas_tool) - 1:
                        llamadas_tool[i] += ")"

            for i in llamadas_tool:
                try:
                    tool = decode_call(i[0], i[1]) if usar_lfm == "n" else decode_call_lfm(i.strip())
                    resultado = ejecutar_tool(tool)
                except Exception as e:
                    resultado = f"Error al ejecutar la herramienta: {e}"

                resultados_tool.append(f"resultado {tool["name"]}: \n{resultado}")
                print(f"\n{resultado}")

            if resultados_tool:
                historial.append({"role": "user", "content": "resultados tool: \n" + "\n---\n".join(resultados_tool)})
            elif AUTONOMO:
                historial.append({"role": "user", "content": "System's message: continue interacting with the workspace"})
            else:
                break