import pandas as pd
import dash
from dash import dcc, html, dash_table, Input, Output
import plotly.express as px
import gunicorn

# URL do Google Sheets (compartilhado publicamente como CSV)
SHEET_ID = "119rDrAyWfXNEp70WdmgvA7OMEbbNX1wZ"
SHEET_NAME = "Dados"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

# Ler dados diretamente do Google Sheets
df = pd.read_csv(URL, skiprows=0)

# Extraindo a data de atualização (presente na primeira linha original da planilha)
first_row = pd.read_csv(URL, nrows=1, header=None)
data_atualizacao = first_row.iloc[0, 1]

# Renomeando colunas
df.rename(columns={
    "Atualizado em: mes_de_referencia": "mes_de_referencia",
    "Histórico dos volumes mensais movimentados no terminal  Em atendimento ao artigo 26, III, d, da Resolução ANP nº 881, de 8 de julho de 2022 nome_do_terminal": "nome_terminal"
}, inplace=True)

# Mapeamento dos valores de sentido da operação
df["sentido_da_operacao"] = df["sentido_da_operacao"].map({1: "Recepção", 2: "Entrega"})

# Converter colunas para os tipos corretos
df['mes_de_referencia'] = pd.to_datetime(df['mes_de_referencia'], format='%Y-%m')
df["volume_m3"] = df["volume_m3"].astype(str).str.replace(',', '.').astype(float)

# Filtrando apenas etanol
df_etanol = df[df["descricao_do_produto"].str.contains("ETANOL", na=False)]

# Separando Recepção e Entrega de Etanol
df_etanol_recebido = df_etanol[df_etanol["sentido_da_operacao"] == "Recepção"].groupby("mes_de_referencia")["volume_m3"].sum().reset_index()
df_etanol_entregue = df_etanol[df_etanol["sentido_da_operacao"] == "Entrega"].groupby("mes_de_referencia")["volume_m3"].sum().reset_index()

# Resumo mensal de outros produtos (ordenado do mais recente para o mais antigo)
df_outros = df[~df["descricao_do_produto"].str.contains("ETANOL", na=False)]
df_resumo_outros = df_outros.groupby(["mes_de_referencia", "descricao_do_produto", "sentido_da_operacao"])["volume_m3"].sum().reset_index()
df_resumo_outros = df_resumo_outros.sort_values(by="mes_de_referencia", ascending=False)  # Ordenando do mais recente para o mais antigo

# Mapeamento do tipo de operação
df["tipo_da_operacao"] = df["tipo_da_operacao"].map({
    1: "Com armazenagem",
    2: "Sem armazenagem",
    3: "Transbordo",
    4: "Abastecimento",
    9: "Outros"
})

# Criando o Dash
app = dash.Dash(__name__)
server = app.server  
app.layout = html.Div([
    html.H1("MONITORAMENTO TECAB - SINDALCOOL"),
    html.H3(f"Última atualização: {data_atualizacao}"),
    
    html.H2("Movimentação de Etanol"),
    dcc.Graph(figure=px.line(df_etanol_recebido, x="mes_de_referencia", y="volume_m3", title="Recebimento de Etanol no Porto")),
    dcc.Graph(figure=px.line(df_etanol_entregue, x="mes_de_referencia", y="volume_m3", title="Entrega de Etanol no Porto")),
    
    html.H2("Análise do Tipo de Operação"),
    html.Div([
        html.Label("Selecione o Produto:"),
        dcc.Dropdown(
            id="dropdown-produto",
            options=[{"label": prod, "value": prod} for prod in df["descricao_do_produto"].unique()],
            value="ETANOL",  # Valor padrão
            clearable=False
        ),
        html.Label("Selecione o Tipo de Operação:"),
        dcc.Dropdown(
            id="dropdown-tipo-operacao",
            options=[{"label": tipo, "value": tipo} for tipo in df["tipo_da_operacao"].unique()],
            value="Com armazenagem",  # Valor padrão
            clearable=False
        ),
        html.Label("Selecione o Sentido da Operação:"),
        dcc.Dropdown(
            id="dropdown-sentido-operacao",
            options=[{"label": sentido, "value": sentido} for sentido in df["sentido_da_operacao"].unique()],
            value="Recepção",  # Valor padrão
            clearable=False
        ),
    ]),
    dcc.Graph(id="grafico-tipo-operacao"),
    dash_table.DataTable(
        id="tabela-tipo-operacao",
        columns=[{"name": i, "id": i} for i in ["mes_de_referencia", "volume_m3"]],
        style_table={'overflowX': 'auto'}
    ),
    
    html.H2("Resumo Mensal de Outros Produtos"),
    dash_table.DataTable(
        columns=[{"name": i, "id": i} for i in df_resumo_outros.columns],
        data=df_resumo_outros.to_dict("records"),
        style_table={'overflowX': 'auto'}
    )
])

# Callback para atualizar o gráfico e a tabela de tipo de operação
@app.callback(
    [Output("grafico-tipo-operacao", "figure"),
     Output("tabela-tipo-operacao", "data")],
    [Input("dropdown-produto", "value"),
     Input("dropdown-tipo-operacao", "value"),
     Input("dropdown-sentido-operacao", "value")]
)
def update_tipo_operacao(produto, tipo_operacao, sentido_operacao):
    # Filtrar os dados com base nas seleções
    filtered_df = df[
        (df["descricao_do_produto"] == produto) &
        (df["tipo_da_operacao"] == tipo_operacao) &
        (df["sentido_da_operacao"] == sentido_operacao)
    ]
    grouped_df = filtered_df.groupby("mes_de_referencia")["volume_m3"].sum().reset_index()
    
    # Criar gráfico
    fig = px.bar(grouped_df, x="mes_de_referencia", y="volume_m3", title=f"Volume de {produto} - {tipo_operacao} ({sentido_operacao})")
    
    # Preparar dados da tabela
    table_data = grouped_df.to_dict("records")
    
    return fig, table_data

if __name__ == "__main__":
    app.run_server(debug=False)
    
