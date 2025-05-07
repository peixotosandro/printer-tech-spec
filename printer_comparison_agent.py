import logging
from flask import Flask, request, render_template_string
from markupsafe import Markup
import markdown
import os
import httpx
from openai import OpenAI

app = Flask(__name__)

# Configuração de logging para depuração
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configuração do cliente OpenAI para a API da xAI com cliente HTTP personalizado
client = OpenAI(
    base_url="https://api.x.ai/v1",
    api_key=os.getenv("XAI_API_KEY"),
    http_client=httpx.Client(proxies=None),
)

# Função para buscar dispositivos com base em especificações fornecidas
def find_equipments(specs):
    messages = [
        {
            "role": "system",
            "content": "You are a highly intelligent AI assistant specialized in finding devices from manufacturers like Lexmark, HP, Ricoh, Epson, Brother that match user-provided technical specifications. Use the most recent official specifications from manufacturers' websites (e.g., www.lexmark.com, www.hp.com, www.ricoh.com, www.epson.com, www.brother-usa.com) as of May 2025. For each manufacturer, identify one device that most closely matches the provided specifications. If no device from a manufacturer meets the majority of the specifications, state 'No matching device'. Return only a table in Markdown format with columns: Specification, Lexmark, HP, Ricoh, Epson, Brother. Include key specifications like speed (ppm), resolution (dpi), connectivity (e.g., 'Wireless' if applicable), functions, paper capacity (sheets), screen size (inches), and approximate price (US$). If data is unavailable, state 'Not available'."
        },
        {
            "role": "user",
            "content": f"Find devices from Lexmark, HP, Ricoh, Epson, and Brother that match these specifications: {specs}. Return only the table, no additional text."
        },
    ]
    
    try:
        logger.debug(f"Calling API with specifications: {specs}")
        completion = client.chat.completions.create(
            model="grok-3-mini-beta",
            messages=messages,
            temperature=0.2,
            max_tokens=3000,
        )
        
        logger.debug(f"Raw API response: {completion}")
        content = completion.choices[0].message.content
        if not content and hasattr(completion.choices[0].message, 'reasoning_content'):
            content = completion.choices[0].message.reasoning_content
        
        return content if content else "Error: No information returned by the API. Check the API key at https://x.ai/api or the documentation at https://docs.x.ai."
    except Exception as e:
        logger.error(f"Error in API call: {str(e)}")
        if "404" in str(e):
            return "Error: Model not found or access denied for your team. Verify your API key at https://x.ai/api and contact support if the issue persists, quoting your team ID."
        return f"Error: {str(e)}. Check the API key at https://x.ai/api or the documentation at https://docs.x.ai."

# Interface web em HTML
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Device Specification Matcher</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        h2 { color: #555; margin-top: 20px; }
        form { margin-bottom: 20px; }
        textarea { padding: 8px; width: 500px; height: 100px; margin-right: 10px; }
        input[type=submit] { padding: 8px 16px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
        .error { color: red; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; font-weight: bold; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        #result { margin-top: 10px; }
    </style>
</head>
<body>
    <h1>Device Specification Matcher</h1>
    <form method="POST">
        <label>Enter Technical Specifications:</label><br>
        <textarea name="specs" placeholder="Ex: Multifunction printer, 40 ppm, 1200x1200 dpi, wireless, print/scan/copy, 500-sheet capacity, 4.3-inch screen" required></textarea><br>
        <input type="submit" value="Find Devices">
    </form>
    {% if result %}
        <h2>Matching Devices</h2>
        {% if "Error" in result %}
            <div class="error">{{ result|safe }}</div>
        {% else %}
            <div id="result">{{ result|safe }}</div>
        {% endif %}
    {% endif %}
</body>
</html>
"""

# Rota principal
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        specs = request.form["specs"]
        markdown_text = find_equipments(specs)
        if "Error" not in markdown_text:
            # Remover escaping manual e converter Markdown para HTML
            cleaned_text = markdown_text.replace('<', '<').replace('>', '>')
            result = Markup(markdown.markdown(cleaned_text, extensions=['tables']))
        else:
            result = Markup(markdown_text)  # Mantém mensagens de erro como texto seguro
    return render_template_string(HTML_TEMPLATE, result=result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)