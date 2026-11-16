import wikipedia

wikipedia.set_lang('es')


def search_articulos(key:str):
    articulos = wikipedia.search(key)
    return f"articulos disponibles: {articulos} --- use the tool 'get_article_wikipedia' to get an article"

def get_articulo(key:str):
    try:
        return f"{wikipedia.summary(key, sentences=5)} \n---Solo se agregaron maximo 5 oraciones del resultado---"
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Hay múltiples opciones:  {e}"
    except wikipedia.exceptions.PageError:
        return "La pagina no existe --- use the tool search_wikipedia to see available articles."