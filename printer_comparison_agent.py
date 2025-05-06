import logging
from flask import Flask, request, render_template_string
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

# Função para comparar equipamentos usando a API da xAI
def compare_equipments(model1, model2):
    messages = [
        {
            "role": "system",
            "content": "You are a highly intelligent AI assistant specialized in comparing technical specifications of equipment. Always respond in English and use exactly the models provided by the user (e.g., Lexmark MX432 must not be confused with MX431 or similar models like MX431adn or MX431adw). Provide only accurate data based on the most recent official specifications from the manufacturer's website (e.g., Lexmark or HP). Cross-check data across multiple official sources to ensure consistency, and if data varies, use the most recent value or note the discrepancy. For enterprise-level models like MX432 or MX632, screen sizes are typically larger (e.g., 4.3 or 7 inches); ensure this is reflected accurately. Return a complete table in Markdown format with the following columns: Specification, [Model1], [Model2], including speed (ppm), resolution (dpi), connectivity (include 'Wireless (optional)' if applicable), functions, paper capacity (sheets), screen size (inches), and approximate price (US$). If data is unavailable, state 'Not available'."
        },
        {
            "role": "user",
            "content": f"Compare the models {model1} and {model2}. Use precise and verified specifications from the manufacturer's official sources, ensuring the exact model is represented (e.g., for Lexmark MX432, use its specific data, not MX431 data)."
        },
    ]
    
    try:
        logger.debug(f"Calling API with models: {model1}, {model2}")
        completion = client.chat.completions.create(
            model="grok-3-mini-beta",
            messages=messages,
            temperature=0.2,  # Low temperature for precision
            max_tokens=2000,
        )
        
        logger.debug(f"Raw API response: {completion}")
        content = completion.choices[0].message.content
        if not content and hasattr(completion.choices[0].message, 'reasoning_content'):
            content = completion.choices[0].message.reasoning_content
        
        return content if content else "Error: No information returned by the API. Check the API key at https://x.ai/api or the documentation at https://docs.x.ai."
    except Exception as e:
        logger.error(f"Error in API call: {str(e)}")
        return f"Error: {str(e)}. Check the API key at https://x.ai/api or the documentation at https://docs.x.ai."

# Interface web em HTML
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Equipment Comparison Agent</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        form { margin-bottom: 20px; }
        input[type=text] { padding: 8px; width: 200px; margin-right: 10px; }
        input[type=submit] { padding: 8px 16px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
        pre { background-color: #f4f4f4; padding: 10px; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word; overflow: auto; max-height: none; }
        .error { color: red; }
    </style>
</head>
<body>
    <h1>Equipment Comparison Agent</h1>
    <form method="POST">
        <label>Model 1:</label>
        <input type="text" name="model1" placeholder="Ex: Lexmark MX432" required>
        <label>Model 2:</label>
        <input type="text" name="model2" placeholder="Ex: Lexmark MX632" required>
        <input type="submit" value="Compare">
    </form>
    {% if result %}
        <h2>Comparison Result</h2>
        {% if "Error" in result %}
            <pre class="error">{{ result }}</pre>
        {% else %}
            <pre>{{ result }}</pre>
        {% endif %}
    {% endif %}
</body>
</html>
"""

# Rota principal
@app.route("/", methods=["GET", "POST"])
def index():
    result = None  # Reinicia o resultado a cada acesso à página
    if request.method == "POST":
        model1 = request.form["model1"]
        model2 = request.form["model2"]
        result = compare_equipments(model1, model2)
    return render_template_string(HTML_TEMPLATE, result=result)

if __name__ == "__main__":
    # Configuração para produção (Render ou outra plataforma)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)