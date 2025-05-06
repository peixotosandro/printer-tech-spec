from openai import OpenAI
from flask import Flask, request, render_template_string
import logging
import os

app = Flask(__name__)

# Configuração de logging para depuração
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configuração do cliente OpenAI para a API da xAI (usando variável de ambiente)
client = OpenAI(
    base_url="https://api.x.ai/v1",
    api_key=os.getenv("XAI_API_KEY"),  # Chave será configurada no ambiente de hospedagem
)

# Função para comparar equipamentos usando a API da xAI
def compare_equipments(model1, model2):
    messages = [
        {
            "role": "system",
            "content": "Você é um assistente de IA altamente inteligente especializado em comparar especificações técnicas de equipamentos. Responda sempre em português e use exatamente os modelos fornecidos pelo usuário.",
        },
        {
            "role": "user",
            "content": f"Compare os modelos {model1} e {model2}. Inclua velocidade (ppm), resolução (dpi), conectividade, funções, capacidade de papel (folhas), tamanho da tela (polegadas) e preço aproximado (R$). Retorne uma tabela em formato Markdown completa."
        },
    ]
    
    try:
        logger.debug(f"Chamando API com modelos: {model1}, {model2}")
        completion = client.chat.completions.create(
            model="grok-3-mini-beta",  # Ou "grok-3-mini-fast-beta"
            reasoning_effort="high",
            messages=messages,
            temperature=0.7,
            max_tokens=3000,
        )
        
        logger.debug(f"Resposta bruta da API: {completion}")
        content = completion.choices[0].message.content
        if not content and hasattr(completion.choices[0].message, 'reasoning_content'):
            content = completion.choices[0].message.reasoning_content
        return content if content else "Nenhuma informação retornada pela API."
    except Exception as e:
        logger.error(f"Erro na chamada à API: {str(e)}")
        return f"Erro: {str(e)}. Verifique a chave de API em https://x.ai/api ou a documentação em https://docs.x.ai."

# Interface web em HTML
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Agente de Comparação de Equipamentos</title>
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
    <h1>Agente de Comparação de Equipamentos</h1>
    <form method="POST">
        <label>Modelo 1:</label>
        <input type="text" name="model1" placeholder="Ex: Lexmark MX421" required>
        <label>Modelo 2:</label>
        <input type="text" name="model2" placeholder="Ex: HP LaserJet Pro M428" required>
        <input type="submit" value="Comparar">
    </form>
    {% if result %}
        <h2>Resultado da Comparação</h2>
        {% if "Erro" in result %}
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