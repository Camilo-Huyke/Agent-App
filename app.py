from openai import OpenAI
import os
import re
from pathlib import Path

import tool_decoder
import tool_search_wikipedia
import tool_run_python

from rich.console import Console
from rich.panel import Panel

client = OpenAI(base_url="http://localhost:1234/v1", api_key="C-137")

PROYECTO = Path("./workspace").resolve()
PROYECTO.mkdir(exist_ok=True)

SYSTEM_PROMPT = ""
AUTONOMO = False
MODEL = "lfm2.5-8B-A1B"
historial = []


def set_system_prompt(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            prompt = f.read()
    except Exception as e:
        print(e)
    return prompt

def safe_path(path:str) -> Path:
    destino = (PROYECTO / path).resolve()

    if not destino.is_relative_to(PROYECTO):
        raise ValueError("Ruta fuera del proyecto")
    
    return destino

def ejecutar_tool(tool: dict) -> str:

    LIMITE_LECTURA = 6000
    MAX_COINCIDENCIAS = 20

    name = tool["name"]

    def required_param(*params):
        missed_params = [m for m in params if tool.get(m) is None]
        if missed_params:
            raise ValueError(f"faltan parametros de {name}: {', '.join(missed_params)}")

    try:

        if name == "write_file":
            required_param("path")
            destino = safe_path(tool["path"])
            exist = destino.exists()
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(tool.get("content", ""), encoding="utf-8")
            return f"OK: file {'overwritten' if exist else 'created' } in {tool['path']}"
        
        elif name == "read_file":
            required_param("path")
            contenido = safe_path(tool["path"]).read_text(encoding="utf-8")
            if not contenido:
                return "(file empty)"
            if len(contenido) > LIMITE_LECTURA:
                restante = len(contenido) - LIMITE_LECTURA
                return contenido[:LIMITE_LECTURA] + f"\n[... Truncado, faltan: {restante} caracteres]"
            return contenido
        
        elif name == "list_directory":
            required_param("path")
            contenido = sorted(
                safe_path(tool["path"]).iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower())
            )
            if not contenido:
                return "(dir empty)"
            return "\n".join(p.name + ("/" if p.is_dir() else "") for p in contenido)
        
        elif name == "append_file":
            required_param("path", "content")
            with open(safe_path(tool["path"]), "a", encoding="utf-8") as f:
                f.write(f"\n{tool['content']}")
            return f"OK: se escribio en {tool['path']}"

        elif name == "grep":
            required_param("path", "pattern")
            patron_text = re.compile(tool["pattern"])
            coincidencias = []
            with open(safe_path(tool["path"]), "r", encoding='utf-8') as f:
                for n, linea in enumerate(f,1):
                    if patron_text.search(linea):
                        coincidencias.append(f"Linea {n}: {linea.strip()}")
                    if len(coincidencias) >= MAX_COINCIDENCIAS:
                        coincidencias.append("[... se omitio el resto de coincidencias]")
                        break
            return "\n".join(coincidencias) or "(No se encontraron coincidencias)"

        elif name == "search_wikipedia":
            required_param("query")
            return tool_search_wikipedia.search_articulos(tool["query"])

        elif name == "get_article_wikipedia":
            required_param("article")
            return tool_search_wikipedia.get_articulo(tool["article"])

        elif name == "run_python_file":
            required_param("path")
            return tool_run_python.run_python(safe_path(tool["path"]))
        
        return f"ERROR: herramienta desconocida '{name}'"
    
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

        if not chunk.choices:
            continue

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
                print("\n\nrespuesta:") #\u25CF
            print(texto, end="", flush=True)
            texto_completo += texto

    print()

    return texto_completo


if __name__ == '__main__':

    mode_compat = input("Ingrese el modo de compatibilidad: ").strip()
    tool_decoder_ = tool_decoder.ToolDecoder(compatiblity_mode=mode_compat)

    if mode_compat == "HTML":
        SYSTEM_PROMPT = set_system_prompt("system_prompt_HTML.txt")
    if mode_compat == "LFM":
        SYSTEM_PROMPT = set_system_prompt("system_prompt_LFM.txt")

    historial.append({"role": "system", "content": SYSTEM_PROMPT})

    while True: 

        msg = input("\n> ").strip()

        if msg.lower() == "/salir":
            break

        historial.append({"role": "user", "content": msg})

        while True:

            texto_completo = send_get_mesg()

            if texto_completo:
                historial.append({"role": "assistant", "content": texto_completo})
            else:
                historial.pop()

            resultados_tool = []
            llamadas_tool = tool_decoder_.find_call(texto_completo)

            for i in llamadas_tool:
                try:
                    tool = tool_decoder_.decode_call(i)
                    resultado = ejecutar_tool(tool)

                    name = tool.get("name", "desconocido")
                except Exception as e:
                    resultado = f"Error al ejecutar la herramienta: {e}"

                resultados_tool.append(f"resultado {name}: \n{resultado}")
                print(f"\n{resultado}")

            if resultados_tool:
                historial.append({"role": "user", "content": "resultados tool: \n" + "\n---\n".join(resultados_tool)})
            elif AUTONOMO:
                historial.append({"role": "user", "content": "System's message: keep interacting with the workspace. Tips: recuerda cerrar las tools con </tool>"})
            else:
                break