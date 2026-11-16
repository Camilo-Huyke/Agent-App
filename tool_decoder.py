import re
import ast

class ToolDecoder:

    def __init__(self, compatiblity_mode):

        self.compatiblity_mode = compatiblity_mode
        self.list_modes = ["HTML", "LFM", "XML"]

        self.check_compatiblity_mode(compatiblity_mode)


    def check_compatiblity_mode(self, param):

        if self.compatiblity_mode not in self.list_modes:
            raise Exception("modo de compatibildiad no existente")
        else:
            self.compatiblity_mode = param
                
    
    def decode_call(self, tool):

        match self.compatiblity_mode:
            case "HTML":
                return self.decode_call_html(tool[0], tool[1])
            case "LFM":
                return self.decode_call_lfm(tool)
            
    def find_call(self, text):

        match self.compatiblity_mode:
            case "HTML":
                return self.find_call_html(text)
            case "LFM":
                return self.find_call_lfm(text)


    def find_call_xml(self, text):
        PATRON_TOOL = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)
        PATRON_FUNCT = re.compile(r"<function=(.*?)>(.*?)</function>", re.DOTALL)

        tools = PATRON_TOOL.findall(text)
        functions = PATRON_FUNCT.findall(tools[0])
        return functions


    def find_call_html(self, text):
        PATRON_TOOL = re.compile(r"<tool\s+([^>]*?)>(.*?)</tool>", re.DOTALL)
        
        return PATRON_TOOL.findall(text) 


    def decode_call_html(self, attrs: str, cuerpo: str):

        PATRON_ATTR = re.compile(r'(\w+)="([^"]*)"', re.DOTALL)
        
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


    def find_call_lfm(self, text):
        PATRON_TOOL_LFM = re.compile(r"<\|tool_call_start\|>\[(.*?)\]<\|tool_call_end\|>", re.DOTALL)

        llamadas_tool = PATRON_TOOL_LFM.findall(text)

        if len(llamadas_tool) == 0:
            return []

        llamadas_tool = llamadas_tool[0].split("),")

        for i in range(len(llamadas_tool)):
            llamadas_tool[i] = llamadas_tool[i].strip()
            if i < len(llamadas_tool) - 1:
                llamadas_tool[i] += ")"

        return llamadas_tool

    def decode_call_lfm(self, call):
        try:
            nodo = ast.parse(call.strip(), mode="eval").body
        except SyntaxError as e:
            raise ValueError(f"llamada mal formada: {e.msg}") from e
 
        if not isinstance(nodo, ast.Call) or not isinstance(nodo.func, ast.Name):
            raise ValueError('la llamada debe tener la forma nombre(arg="valor", ...)')
 
        if nodo.args:
            raise ValueError('usa argumentos con nombre, por ejemplo read_file(path="a.txt")')
 
        tool = {"name": nodo.func.id}
 
        for kw in nodo.keywords:
            if kw.arg is None:
                raise ValueError("no se admite **kwargs")
            try:
                tool[kw.arg] = ast.literal_eval(kw.value)
            except ValueError:
                raise ValueError(f"valor no válido para '{kw.arg}': debe ser un literal") from None
        return tool
            