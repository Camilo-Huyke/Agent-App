import subprocess

def run_python(file_path:str):
    resultado = subprocess.run(['python', file_path], capture_output=True, text=True)

    return resultado.stderr if resultado.stderr else resultado.stdout