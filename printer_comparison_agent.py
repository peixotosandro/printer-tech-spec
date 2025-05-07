import logging
from flask import Flask, request, render_template_string
from markupsafe import escape
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

# Função para comparar dispositivos usando a API da xAI
def compare_equipments(model1, model2):
    messages = [
        {
            "role": "system",
            "content": "You are a highly intelligent AI assistant specialized in comparing technical specifications of devices. Always respond in English and use exactly the models provided (Lexmark MX432 must use only MX432adwe data, not MX431 or similar models). Provide accurate data based on the most recent official specifications from the manufacturer's website (www.lexmark.com for Lexmark, www.ricoh.com for Ricoh, www.hp.com for HP), cross-checked with the latest product pages and support documentation as of May 2025. Avoid outdated or generalized data. For enterprise-level models like MX432 or MX632, screen sizes must be 4.3 or 7 inches. Return a complete table in Markdown format with columns: Specification, [Model1], [Model2], including speed (ppm), resolution (dpi), connectivity (include 'Wireless (optional)' if applicable), functions, paper capacity (sheets), screen size (inches), and approximate price (US$). If data is unavailable, state 'Not available'."
        },
        {
            "role": "user",
            "content": f"Compare the models {model1} and {model2}. Use precise and verified specifications from the manufacturer's official sources, ensuring the exact model is represented."
        },
    ]
    
    try:
        logger.debug(f"Calling API with models: {model1}, {model2}")
        completion = client.chat.completions.create(
            model="grok-3-mini-beta",
            messages=messages,
            temperature=0.2,
            max_tokens=2000,
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
    <title>Device Comparison Agent</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        h2 { color: #555; margin-top: 20px; }
        form { margin-bottom: 20px; }
        input[type=text] { padding: 8px; width: 200px; margin-right: 10px; }
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
    <h1>Device Comparison Agent</h1>
    <form method="POST">
        <label>Model 1:</label>
        <input type="text" name="model1" placeholder="Ex: Lexmark MX432" required>
        <label>Model 2:</label>
        <input type="text" name="model2" placeholder="Ex: Lexmark MX622" required>
        <input type="submit" value="Compare">
    </form>
    {% if result %}
        <h2>Comparison Result</h2>
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
        model1 = request.form["model1"]
        model2 = request.form["model2"]
        markdown_text = compare_equipments(model1, model2)
        if "Error" not in markdown_text:
            # Converter Markdown para HTML no servidor
            result = markdown.markdown(markdown_text, extensions=['tables'])
        else:
            result = markdown_text
    return render_template_string(HTML_TEMPLATE, result=escape(result) if result else None)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)