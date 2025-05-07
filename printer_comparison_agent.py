import logging
from flask import Flask, request, render_template_string
from markupsafe import Markup
import markdown
import os
import httpx
from openai import OpenAI
from datetime import datetime

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

# Função para buscar dispositivos com base em especificações e fabricantes fornecidos
def find_equipments(input_text):
    current_date = datetime.now().strftime("%d/%m/%Y")
    messages = [
        {
            "role": "system",
            "content": f"Você é um assistente de IA altamente inteligente especializado em encontrar dispositivos de fabricantes que correspondam a especificações técnicas fornecidas pelo usuário. Use as especificações mais recentes de sites oficiais dos fabricantes (ex.: www.lexmark.com, www.hp.com, www.ricoh.com, www.epson.com, www.brother-usa.com, ou outros sites oficiais relevantes) até a data atual ({current_date}). O usuário fornecerá um texto contendo os fabricantes desejados (ex.: Lexmark, HP, Canon) e as especificações técnicas (ex.: impressora multifuncional, 40 ppm). Identifique todos os fabricantes mencionados no texto e as especificações a partir dele. Para cada fabricante identificado, liste todos os dispositivos que correspondam à maioria das especificações fornecidas em uma tabela. Se nenhum dispositivo de um fabricante atender à maioria das especificações ou se o fabricante não for reconhecido com dados disponíveis, indique 'Nenhum dispositivo correspondente ou fabricante não reconhecido' na coluna Dispositivo para esse fabricante. Retorne apenas uma tabela em formato Markdown com as colunas: Fabricante, Dispositivo, Velocidade (ppm), Resolução (dpi), Conectividade, Funções, Capacidade de papel (folhas), Tamanho da tela (polegadas), Preço aproximado (US$). Cada linha deve representar um dispositivo específico. Se os dados não estiverem disponíveis, indique 'Não disponível'."
        },
        {
            "role": "user",
            "content": f"Analise o seguinte texto e encontre dispositivos que correspondam às especificações: {input_text}. Retorne apenas a tabela, sem texto adicional."
        },
    ]
    
    try:
        logger.debug(f"Calling API with input: {input_text}")
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
        
        return content if content else "Erro: Nenhuma informação retornada pela API. Verifique a chave de API em https://x.ai/api ou a documentação em https://docs.x.ai."
    except Exception as e:
        logger.error(f"Erro na chamada da API: {str(e)}")
        if "404" in str(e):
            return "Erro: Modelo não encontrado ou acesso negado para sua equipe. Verifique sua chave de API em https://x.ai/api e contate o suporte se o problema persistir, informando seu ID de equipe."
        return f"Erro: {str(e)}. Verifique a chave de API em https://x.ai/api ou a documentação em https://docs.x.ai."

# Interface web em HTML
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Pesquisa de Dispositivos</title>
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
    <h1>Pesquisa de Dispositivos</h1>
    <form method="POST">
        <label>Insira os Fabricantes e Especificações Técnicas:</label><br>
        <textarea name="input_text" placeholder="Lexmark, HP, Canon, Impressora multifuncional, 40 ppm, 1200x1200 dpi, sem fio, impressão/digitalização/cópia, capacidade de 500 folhas, tela de 4,3 polegadas" required></textarea><br>
        <input type="submit" value="Encontrar Dispositivos">
    </form>
    {% if result %}
        <h2>Dispositivos Correspondentes</h2>
        {% if "Erro" in result %}
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
        if "input_text" not in request.form or not request.form["input_text"].strip():
            result = Markup("Erro: O campo de fabricantes e especificações não pode estar vazio.")
        else:
            input_text = request.form["input_text"]
            markdown_text = find_equipments(input_text)
            if "Erro" not in markdown_text:
                cleaned_text = markdown_text.replace('<', '<').replace('>', '>')
                result = Markup(markdown.markdown(cleaned_text, extensions=['tables']))
            else:
                result = Markup(markdown_text)
    return render_template_string(HTML_TEMPLATE, result=result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)