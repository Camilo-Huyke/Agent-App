import tool_decoder
import tool_run_python

text = """<tool_call>
<function=get_candidate_status>
<parameter=candidate_id>
12345
</parameter>
</function>
<function=get_weather>
<parameter=city_name>
Madrid
</parameter>
</function>
</tool_call>"""

decoder = tool_decoder.ToolDecoder(compatiblity_mode="XML")

print(decoder.find_call_xml(text=text))


