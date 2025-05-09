import logging
from flask import Flask, request, render_template_string
from markupsafe import Markup
import markdown
import os
import google.generativeai as genai
from datetime import datetime, timedelta

app = Flask(__name__)

# Configuração de logging para depuração
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configuração do cliente Gemini AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Função para buscar dispositivos com base em especificações e fabricantes fornecidos
def find_equipments(input_text):
    current_date = datetime.now().strftime("%d/%m/%Y")
    prompt = f"""
Você é um assistente de IA altamente inteligente especializado em encontrar dispositivos de fabricantes que correspondam a especificações técnicas fornecidas pelo usuário. Use as especificações mais recentes de sites oficiais dos fabricantes (ex.: www.lexmark.com, www.hp.com, www.ricoh.com, www.epson.com, www.brother-usa.com, ou outros sites oficiais relevantes) até a data atual {current_date}. O usuário fornecerá um texto contendo os fabricantes desejados (ex.: Lexmark, HP, Canon) e as especificações técnicas (ex.: impressora, multifuncional, 40 ppm, tela 4,3 polegadas).

Analise o texto fornecido pelo usuário. Identifique todos os fabricantes mencionados e as especificações técnicas detalhadas. Para cada fabricante identificado, liste *todos* os modelos de dispositivos por ordem de lançamento (os mais novos primero) que correspondam *exatamente* às especificações fornecidas ou que se aproximem o *máximo possível* delas, priorizando os critérios mais importantes mencionados pelo usuário no texto de entrada.

Se nenhum dispositivo recente de um fabricante atender às especificações, ou se o fabricante não for reconhecido com dados disponíveis, indique 'Nenhum dispositivo recente correspondente ou fabricante não reconhecido' na coluna 'Dispositivo' para esse fabricante.

Retorne uma tabela em formato Markdown com as seguintes colunas:

* Fabricante
* Dispositivo
* Printing Technology
* Functions
* Print Speed (ppm)
* Print Resolution (dpi)
* Monthly Duty Cycle
* Paper Capacity
* Supported Media Types
* Connectivity
* Screen Size
* Preço aproximado (US$)

Cada linha da tabela deve representar um dispositivo específico. Se os dados para alguma coluna não estiverem disponíveis (incluindo Screen Size), indique 'Não disponível'. É crucial incluir *todos* os modelos recentes de *todos* os fabricantes mencionados que atendam aos critérios fornecidos, sem limitar o número de resultados por fabricante.

Analise o seguinte texto e encontre dispositivos que correspondam às especificações: {input_text}. Retorne apenas a tabela em formato Markdown, sem qualquer texto introdutório ou adicional antes ou depois da tabela, e sem envolver a tabela em blocos de código (como ```).
"""
    
    try:
        logger.debug(f"Calling Gemini API with input: {input_text}")
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 7000,
            }
        )
        
        logger.debug(f"Raw API response: {response.text}")
        content = response.text.strip()
        
        # Normalize the response and extract only the Markdown table
        lines = content.split('\n')
        table_lines = []
        found_table = False
        inside_code_block = False
        
        for line in lines:
            line = line.strip()
            
            # Detect code block markers
            if line.startswith('```'):
                inside_code_block = not inside_code_block
                continue
                
            # Skip lines if we're inside a code block but haven't found the table yet
            if inside_code_block and not found_table:
                continue
                
            # Identify the start of the table
            if line.startswith('|') and not found_table:
                found_table = True
            if found_table and line:
                table_lines.append(line)
        
        if not table_lines:
            return "Erro: Nenhuma tabela encontrada na resposta da API."
        
        normalized_content = '\n'.join(table_lines)
        logger.debug(f"Normalized content (table only): {normalized_content}")
        
        return normalized_content if normalized_content else "Erro: Nenhuma informação retornada pela API. Verifique a chave de API em https://makersuite.google.com/app/apikey ou a documentação em https://ai.google.dev."
    except Exception as e:
        logger.error(f"Erro na chamada da API: {str(e)}")
        if "403" in str(e) or "401" in str(e):
            return "Erro: Acesso negado ou chave de API inválida. Verifique sua chave de API em https://makersuite.google.com/app/apikey e contate o suporte se o problema persistir."
        return f"Erro: {str(e)}. Verifique a chave de API em https://makersuite.google.com/app/apikey ou a documentação em https://ai.google.dev."

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
        pre { background-color: #f9f9f9; padding: 10px; border: 1px solid #ddd; white-space: pre-wrap; }
    </style>
</head>
<body>
    <h1>Pesquisa de Dispositivos</h1>
    <form method="POST">
        <label>Insira os Fabricantes e Especificações Técnicas:</label><br>
        <textarea name="input_text" placeholder="Lexmark, HP, Canon, Impressora multifuncional, 40 ppm, 1200x1200 dpi, sem fio, impressão/digitalização/cópia, capacidade de 500 folhas, tela maior ou igual a 4,3 polegadas" required></textarea><br>
        <input type="submit" value="Encontrar Dispositivos">
    </form>
    {% if result %}
        <h2>Dispositivos Correspondentes</h2>
        {% if "Erro" in result %}
            <div class="error">{{ result|safe }}</div>
        {% else %}
            {% if result_html %}
                <div id="result">{{ result_html|safe }}</div>
            {% else %}
                <div class="error">Erro: Falha na conversão de Markdown para HTML. Exibindo texto bruto:</div>
                <pre>{{ result_raw }}</pre>
            {% endif %}
        {% endif %}
    {% endif %}
</body>
</html>
"""

# Rota principal
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    result_raw = None
    result_html = None
    if request.method == "POST":
        if "input_text" not in request.form or not request.form["input_text"].strip():
            result = Markup("Erro: O campo de fabricantes e especificações não pode estar vazio.")
        else:
            input_text = request.form["input_text"]
            markdown_text = find_equipments(input_text)
            if "Erro" not in markdown_text:
                cleaned_text = markdown_text.replace('<', '<').replace('>', '>')
                result_raw = cleaned_text
                try:
                    html_result = markdown.markdown(cleaned_text, extensions=['tables'])
                    logger.debug(f"HTML result after Markdown conversion: {html_result}")
                    result_html = Markup(html_result) if html_result else None
                except Exception as e:
                    logger.error(f"Erro na conversão de Markdown para HTML: {str(e)}")
                    result_html = None
                result = result_raw
            else:
                result = Markup(markdown_text)
    return render_template_string(HTML_TEMPLATE, result=result, result_raw=result_raw, result_html=result_html)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
