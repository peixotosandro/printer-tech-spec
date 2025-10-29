import os
import requests
import streamlit as st
import markdown
from datetime import datetime

# -----------------------------
# Configurações básicas
# -----------------------------
st.set_page_config(page_title="Pesquisa de Dispositivos - Grok AI", layout="wide")
API_KEY = os.getenv("GROK_API_KEY")
API_URL = "https://api.x.ai/v1/chat/completions"

# -----------------------------
# Função principal - chamada à API do Grok
# -----------------------------
def find_equipments(input_text):
    current_date = datetime.now().strftime("%d/%m/%Y")

    prompt = f"""
Você é um assistente de IA especializado em encontrar dispositivos de fabricantes que correspondam às especificações técnicas fornecidas.
Use as especificações mais recentes até {current_date} de fabricantes como Lexmark, HP, Canon, Xerox, Ricoh, Epson e Brother.

O usuário fornecerá texto com fabricantes e especificações (ex.: Lexmark, HP, multifuncional, 40 ppm, tela 4,3 polegadas).

Retorne **apenas** uma tabela em formato Markdown, com as colunas:

| Fabricante | Dispositivo | Printing Technology | Functions | Print Speed (ppm) | Print Resolution (dpi) | Monthly Duty Cycle | Paper Capacity | Supported Media Types | Connectivity | Screen Size | Preço aproximado (US$) |

Cada linha representa um modelo real. Se não houver dados, escreva "Não disponível".

Entrada do usuário:
{input_text}

Não inclua texto antes ou depois da tabela.
"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "grok-beta",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data)
        response.raise_for_status()
        reply = response.json()

        # Extrai o texto do modelo
        content = reply["choices"][0]["message"]["content"].strip()

        # Pega apenas a tabela Markdown
        lines = content.splitlines()
        table_lines = [l for l in lines if l.strip().startswith("|")]
        if not table_lines:
            return "Erro: Nenhuma tabela Markdown encontrada na resposta."

        table_md = "\n".join(table_lines)

        # Correção manual conhecida (Lexmark MX942)
        if "MX942" in table_md:
            table_md = table_md.replace("2.8-inch LCD", "10.1-inch color touch screen")

        return table_md

    except requests.exceptions.HTTPError as e:
        if e.response.status_code in [401, 403]:
            return "Erro: Chave de API inválida ou acesso negado. Verifique sua variável GROK_API_KEY."
        return f"Erro HTTP: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"Erro ao chamar API do Grok: {str(e)}"

# -----------------------------
# Interface Streamlit
# -----------------------------
st.title("🔍 Pesquisa de Dispositivos com Grok AI")
st.markdown(
    "Insira os fabricantes e especificações desejadas. O assistente Grok buscará os modelos mais recentes e compatíveis."
)

input_text = st.text_area(
    "Fabricantes e Especificações:",
    placeholder="Exemplo: Lexmark, HP, Impressora multifuncional, 40 ppm, 1200x1200 dpi, tela maior que 4,3 polegadas",
    height=120
)

if st.button("Encontrar Dispositivos"):
    if not input_text.strip():
        st.error("Por favor, insira as especificações antes de continuar.")
    else:
        with st.spinner("Consultando o Grok AI..."):
            result = find_equipments(input_text)

        if result.startswith("Erro"):
            st.error(result)
        else:
            try:
                result_html = markdown.markdown(result, extensions=["tables"])
                st.markdown(result_html, unsafe_allow_html=True)
            except Exception:
                st.warning("Falha ao converter Markdown para HTML. Exibindo texto bruto:")
                st.text(result)

st.divider()
st.caption("Desenvolvido com 💡 por Sandro • Usando Grok API (xAI) e Streamlit")

