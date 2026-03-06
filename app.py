# APP V2 TECAB DASHBOARD (PART 1/3)
# Imports
import pandas as pd
import dash
from dash import dcc, html, dash_table, Input, Output, State
import plotly.express as px
import dash_bootstrap_components as dbc
import numpy as np

# =========================
# CONFIG GOOGLE SHEETS
# =========================

SHEET_ID = "119rDrAyWfXNEp70WdmgvA7OMEbbNX1wZ" 
SHEET_NAME = "Dados"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

# =========================
# ROBUST DATA LOADER
# =========================

def load_and_preprocess_data(url):

    # carregar csv bruto
    df = pd.read_csv(url, skiprows=1)

    # primeira linha contém data atualização
    first_row = pd.read_csv(url, nrows=1, header=None)

    data_atualizacao = first_row.iloc[0,1]

    # corrigir nomes de colunas quebrados
    df.columns = [c.split()[-1] for c in df.columns]

    # garantir colunas corretas
    expected_cols = [
        "mes_de_referencia",
        "codigo_anp_do_terminal",
        "nome_do_terminal",
        "municipio_do_terminal",
        "uf",
        "sentido_da_operacao",
        "tipo_da_operacao",
        "modo_de_transporte",
        "codigo_anp_do_produto",
        "descricao_do_produto",
        "volume_m3"
    ]

    df = df.iloc[:, :len(expected_cols)]
    df.columns = expected_cols

    # converter data
    df["mes_de_referencia"] = pd.to_datetime(
        df["mes_de_referencia"],
        errors="coerce"
    )

    # converter volume
    df["volume_m3"] = (
        df["volume_m3"]
        .astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )

    df["volume_m3"] = pd.to_numeric(
        df["volume_m3"],
        errors="coerce"
    ).fillna(0)

    # mapear códigos
    df["sentido_da_operacao"] = df["sentido_da_operacao"].map({
        1:"Recepção",
        2:"Entrega"
    })

    df["tipo_da_operacao"] = df["tipo_da_operacao"].map({
        1:"Com armazenagem",
        2:"Sem armazenagem",
        3:"Transbordo",
        4:"Abastecimento",
        9:"Outros"
    })

    # criar ano e mes
    df["ano"] = df["mes_de_referencia"].dt.year
    df["mes"] = df["mes_de_referencia"].dt.month

    # separar etanol
    df_etanol = df[
        df["descricao_do_produto"]
        .astype(str)
        .str.contains("ETANOL", na=False)
    ]

    df_outros = df[
        ~df["descricao_do_produto"]
        .astype(str)
        .str.contains("ETANOL", na=False)
    ]

    df_resumo_outros = df_outros.groupby(
        ["mes_de_referencia","descricao_do_produto","sentido_da_operacao"]
    )["volume_m3"].sum().reset_index()

    return df, data_atualizacao, df_etanol, df_resumo_outros



# =========================
# LOAD DATA
# =========================

df, data_atualizacao, df_etanol, df_resumo_outros = load_and_preprocess_data(URL)

# =========================
# KPI CALCULATIONS
# =========================

def calculate_kpis(df_data):

    latest_month = df_data['mes_de_referencia'].max()

    previous_month = latest_month - pd.DateOffset(months=1)

    df_latest = df_data[df_data['mes_de_referencia'] == latest_month]

    df_previous = df_data[df_data['mes_de_referencia'] == previous_month]

    total_volume_latest = df_latest['volume_m3'].sum()

    total_volume_previous = df_previous['volume_m3'].sum()

    etanol_recepcao_latest = df_latest[
        df_latest['descricao_do_produto'].astype(str).str.contains("ETANOL", na=False) &
        (df_latest['sentido_da_operacao']=="Recepção")
    ]['volume_m3'].sum()

    etanol_entrega_latest = df_latest[
        df_latest['descricao_do_produto'].astype(str).str.contains("ETANOL", na=False) &
        (df_latest['sentido_da_operacao']=="Entrega")
    ]['volume_m3'].sum()

    growth_total = ((total_volume_latest-total_volume_previous)/total_volume_previous*100) if total_volume_previous>0 else 0

    return {
        "total_volume": total_volume_latest,
        "growth_total": growth_total,
        "etanol_recepcao": etanol_recepcao_latest,
        "etanol_entrega": etanol_entrega_latest,
        "latest_month": latest_month.strftime("%B/%Y") if pd.notna(latest_month) else ""
    }

kpis = calculate_kpis(df)

# =========================
# DASH APP
# =========================

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Dashboard TECAB V2"

server = app.server

# =========================
# LAYOUT (PART 1)
# =========================

app.layout = dbc.Container([

html.H1("Dashboard de Movimentação de Combustíveis - TECAB",className="text-center my-3"),

html.H6(f"Última atualização: {data_atualizacao}",className="text-center text-muted"),

html.H6(f"Mês de referência: {kpis['latest_month']}",className="text-center text-muted mb-3"),

html.Hr(),

# KPI ROW

dbc.Row([

    dbc.Col(dbc.Card([
        dbc.CardHeader("Volume Total Movimentado"),
        dbc.CardBody([
            html.H2(f"{kpis['total_volume']:,.0f} m³",className="text-center"),
            html.P(f"Crescimento: {kpis['growth_total']:.2f}%",className="text-center")
        ])
    ]),md=4),

    dbc.Col(dbc.Card([
        dbc.CardHeader("Etanol Recebido"),
        dbc.CardBody([
            html.H2(f"{kpis['etanol_recepcao']:,.0f} m³",className="text-center")
        ])
    ]),md=4),

    dbc.Col(dbc.Card([
        dbc.CardHeader("Etanol Entregue"),
        dbc.CardBody([
            html.H2(f"{kpis['etanol_entrega']:,.0f} m³",className="text-center")
        ])
    ]),md=4)

]),

html.Br(),

# MAIN TABS

dbc.Tabs([

    dbc.Tab(label="Visão Geral Etanol",children=[

        dbc.Row([

            dbc.Col(dcc.Graph(id="graph-etanol-recebido"),md=6),

            dbc.Col(dcc.Graph(id="graph-etanol-entregue"),md=6)

        ])

    ]),

    dbc.Tab(label="Análise Avançada",children=[

        dbc.Row([

            dbc.Col(dcc.Graph(id="grafico-yoy"),md=6),

            dbc.Col(dcc.Graph(id="grafico-ytd"),md=6)

        ]),

        dbc.Row([

            dbc.Col(dcc.Graph(id="grafico-heatmap"),md=6),

            dbc.Col(dcc.Graph(id="grafico-share-produtos"),md=6)

        ])

    ])

]),

# STORE

dcc.Store(id='filtered-data-store')

],fluid=True)

# =========================
# CALLBACKS (PART 2)
# =========================

# -------- ETANOL RECEBIDO / ENTREGUE --------

@app.callback(
    Output("graph-etanol-recebido","figure"),
    Input("main-tabs","active_tab")
)
def update_etanol_recebido(_):

    df_recebido = df_etanol[df_etanol["sentido_da_operacao"]=="Recepção"]

    data = df_recebido.groupby("mes_de_referencia")["volume_m3"].sum().reset_index()

    fig = px.line(
        data,
        x="mes_de_referencia",
        y="volume_m3",
        markers=True,
        title="Volume de Etanol Recebido (m³)"
    )

    fig.update_layout(template="plotly_white",hovermode="x unified")

    return fig


@app.callback(
    Output("graph-etanol-entregue","figure"),
    Input("main-tabs","active_tab")
)
def update_etanol_entregue(_):

    df_entregue = df_etanol[df_etanol["sentido_da_operacao"]=="Entrega"]

    data = df_entregue.groupby("mes_de_referencia")["volume_m3"].sum().reset_index()

    fig = px.line(
        data,
        x="mes_de_referencia",
        y="volume_m3",
        markers=True,
        title="Volume de Etanol Entregue (m³)"
    )

    fig.update_layout(template="plotly_white",hovermode="x unified")

    return fig


# -------- YOY ANALYSIS --------

@app.callback(
    Output("grafico-yoy","figure"),
    Input("main-tabs","active_tab")
)
def update_yoy(_):

    data = df.groupby(["ano","mes"])["volume_m3"].sum().reset_index()

    fig = px.line(
        data,
        x="mes",
        y="volume_m3",
        color="ano",
        markers=True,
        title="Comparação Anual da Movimentação"
    )

    fig.update_layout(template="plotly_white")

    return fig


# -------- YTD --------

@app.callback(
    Output("grafico-ytd","figure"),
    Input("main-tabs","active_tab")
)
def update_ytd(_):

    data = df.groupby(["ano","mes"])["volume_m3"].sum().reset_index()

    data["ytd"] = data.groupby("ano")["volume_m3"].cumsum()

    fig = px.line(
        data,
        x="mes",
        y="ytd",
        color="ano",
        markers=True,
        title="Volume Acumulado no Ano (YTD)"
    )

    fig.update_layout(template="plotly_white")

    return fig


# -------- HEATMAP SAZONAL --------

@app.callback(
    Output("grafico-heatmap","figure"),
    Input("main-tabs","active_tab")
)
def update_heatmap(_):

    data = df.groupby(["ano","mes"])["volume_m3"].sum().reset_index()

    pivot = data.pivot(index="ano",columns="mes",values="volume_m3")

    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale="YlOrRd",
        title="Heatmap de Sazonalidade"
    )

    return fig


# -------- PARTICIPAÇÃO PRODUTOS --------

@app.callback(
    Output("grafico-share-produtos","figure"),
    Input("main-tabs","active_tab")
)
def update_share(_):

    data = df.groupby("descricao_do_produto")["volume_m3"].sum().reset_index()

    fig = px.pie(
        data,
        values="volume_m3",
        names="descricao_do_produto",
        hole=0.5,
        title="Participação dos Produtos"
    )

    return fig


# =========================
# CALLBACKS (PART 3)
# =========================

# -------- ANÁLISE DETALHADA / FILTROS --------

@app.callback(
    Output('filtered-data-store','data'),
    [Input('graph-etanol-recebido','id')]
)
def initialize_store(_):

    # inicializa store com dataset completo
    return df.to_dict('records')


@app.callback(
    Output('filtered-data-store','data', allow_duplicate=True),
    [Input('filtered-data-store','data')],
    prevent_initial_call=True
)
def refresh_store(data):

    # placeholder para futuras expansões de filtro
    return data


# -------- RANKING DE PRODUTOS --------

@app.callback(
    Output('ranking-produtos','figure'),
    Input('main-tabs','active_tab'),
    prevent_initial_call=True
)
def update_ranking(_):

    data = (
        df.groupby('descricao_do_produto')['volume_m3']
        .sum()
        .reset_index()
        .sort_values('volume_m3',ascending=False)
    )

    fig = px.bar(
        data,
        x='descricao_do_produto',
        y='volume_m3',
        title='Ranking de Produtos Movimentados',
        color='volume_m3'
    )

    fig.update_layout(template='plotly_white')

    return fig


# -------- BARRAS EMPILHADAS GLOBAL --------

@app.callback(
    Output('grafico-barras-empilhadas-global','figure'),
    Input('main-tabs','active_tab'),
    prevent_initial_call=True
)
def update_stacked_global(_):

    data = df.groupby(['mes_de_referencia','tipo_da_operacao'])['volume_m3'].sum().reset_index()

    fig = px.bar(
        data,
        x='mes_de_referencia',
        y='volume_m3',
        color='tipo_da_operacao',
        barmode='stack',
        title='Movimentação por Tipo de Operação'
    )

    fig.update_layout(template='plotly_white',hovermode='x unified')

    return fig


# -------- TABELA ANALÍTICA --------

@app.callback(
    Output('tabela-analitica','data'),
    Input('main-tabs','active_tab'),
    prevent_initial_call=True
)
def update_table(_):

    data = (
        df.groupby(['mes_de_referencia','descricao_do_produto','sentido_da_operacao'])['volume_m3']
        .sum()
        .reset_index()
        .sort_values('mes_de_referencia',ascending=False)
    )

    return data.to_dict('records')


# =========================
# EXTRA ANALYTICS (TECAB)
# =========================

# crescimento mensal

def calculate_growth_series():

    data = df.groupby('mes_de_referencia')['volume_m3'].sum().reset_index()

    data['growth_pct'] = data['volume_m3'].pct_change()*100

    return data


# share etanol

def calculate_etanol_share():

    total = df.groupby('mes_de_referencia')['volume_m3'].sum()

    etanol = df[df['descricao_do_produto'].str.contains('ETANOL',na=False)]

    etanol = etanol.groupby('mes_de_referencia')['volume_m3'].sum()

    share = (etanol/total*100).reset_index(name='etanol_share')

    return share


# =========================
# SERVER
# =========================

server = app.server


# =========================
# RUN
# =========================

if __name__ == '__main__':

    app.run_server(
        host='0.0.0.0',
        port=8050,
        debug=False
    )



