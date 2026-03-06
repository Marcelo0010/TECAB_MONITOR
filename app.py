import pandas as pd
import dash
from dash import dcc, html, dash_table, Input, Output
import plotly.express as px
import dash_bootstrap_components as dbc

# ==========================================
# CONFIG GOOGLE SHEETS
# ==========================================

SHEET_ID = "119rDrAyWfXNEp70WdmgvA7OMEbbNX1wZ"
SHEET_NAME = "Dados"

URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

# ==========================================
# LOAD DATA
# ==========================================

def load_data():

    first_row = pd.read_csv(URL, nrows=1, header=None)
    data_atualizacao = first_row.iloc[0,1] if first_row.shape[1] > 1 else ""

    df = pd.read_csv(URL, skiprows=2)

    df.columns = df.columns.str.strip()

    df["mes_de_referencia"] = pd.to_datetime(df["mes_de_referencia"], errors="coerce")

    df["volume_m3"] = (
        df["volume_m3"]
        .astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )

    df["volume_m3"] = pd.to_numeric(df["volume_m3"], errors="coerce").fillna(0)

    df["sentido_da_operacao"] = df["sentido_da_operacao"].map({
        1: "Recepção",
        2: "Entrega"
    })

    df["tipo_da_operacao"] = df["tipo_da_operacao"].map({
        1: "Com armazenagem",
        2: "Sem armazenagem",
        3: "Transbordo",
        4: "Abastecimento",
        9: "Outros"
    })

    df["modo_de_transporte"] = df["modo_de_transporte"].map({
        1: "Rodoviário",
        2: "Ferroviário",
        4: "Aquaviário",
        5: "Dutoviário",
        9: "Outros"
    })

    return df, data_atualizacao


# ==========================================
# ANALYTICS
# ==========================================

def calculate_kpis(df):

    latest = df["mes_de_referencia"].max()
    previous = latest - pd.DateOffset(months=1)

    df_latest = df[df["mes_de_referencia"] == latest]
    df_prev = df[df["mes_de_referencia"] == previous]

    total_latest = df_latest["volume_m3"].sum()
    total_prev = df_prev["volume_m3"].sum()

    growth = ((total_latest-total_prev)/total_prev*100) if total_prev > 0 else 0

    etanol = df[df["descricao_do_produto"].str.contains("ETANOL", na=False)]

    etanol_rec = etanol[etanol["sentido_da_operacao"]=="Recepção"]["volume_m3"].sum()
    etanol_ent = etanol[etanol["sentido_da_operacao"]=="Entrega"]["volume_m3"].sum()

    return {

        "latest_month": latest.strftime("%B/%Y"),

        "total_volume": total_latest,

        "growth_total": growth,

        "etanol_recebido": etanol_rec,

        "etanol_entregue": etanol_ent

    }


# ==========================================
# LOAD DATA
# ==========================================

df, data_atualizacao = load_data()

kpis = calculate_kpis(df)

# ==========================================
# DASH APP
# ==========================================

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP]
)

server = app.server


# ==========================================
# LAYOUT
# ==========================================

app.layout = dbc.Container([

    html.H1(
        "Dashboard de Movimentação de Combustíveis - TECAB",
        className="text-center my-3"
    ),

    html.H6(
        f"Última atualização: {data_atualizacao}",
        className="text-center text-muted"
    ),

    html.H6(
        f"Mês de referência: {kpis['latest_month']}",
        className="text-center text-muted mb-3"
    ),

    html.Hr(),

    dbc.Row([

        dbc.Col(dbc.Card([
            dbc.CardHeader("Volume Total Movimentado"),
            dbc.CardBody(html.H2(f"{kpis['total_volume']:,.0f} m³", className="text-center"))
        ]), md=4),

        dbc.Col(dbc.Card([
            dbc.CardHeader("Etanol Recebido"),
            dbc.CardBody(html.H2(f"{kpis['etanol_recebido']:,.0f} m³", className="text-center"))
        ]), md=4),

        dbc.Col(dbc.Card([
            dbc.CardHeader("Etanol Entregue"),
            dbc.CardBody(html.H2(f"{kpis['etanol_entregue']:,.0f} m³", className="text-center"))
        ]), md=4)

    ], className="mb-4"),

    dbc.Tabs([

        dbc.Tab(label="Histórico Geral", children=[

            dcc.Graph(id="grafico-historico"),

            dbc.Row([

                dbc.Col(dcc.Graph(id="grafico-produto-share"), md=6),

                dbc.Col(dcc.Graph(id="grafico-operacao"), md=6)

            ])

        ]),

        dbc.Tab(label="Logística", children=[

            dcc.Graph(id="grafico-transporte")

        ]),

        dbc.Tab(label="Sazonalidade", children=[

            dcc.Graph(id="grafico-sazonal")

        ]),

        dbc.Tab(label="Ranking Produtos", children=[

            dcc.Graph(id="grafico-ranking")

        ]),

        dbc.Tab(label="Base de Dados", children=[

            dash_table.DataTable(

                data=df.to_dict("records"),

                columns=[{"name": i, "id": i} for i in df.columns],

                page_size=20,

                filter_action="native",

                sort_action="native",

                export_format="csv",

                style_table={"overflowX":"auto"},

                style_header={
                    "backgroundColor":"#2c3e50",
                    "color":"white"
                }

            )

        ])

    ])

], fluid=True)


# ==========================================
# CALLBACKS
# ==========================================

@app.callback(
    Output("grafico-historico","figure"),
    Input("grafico-historico","id")
)
def historico(_):

    data = df.groupby("mes_de_referencia")["volume_m3"].sum().reset_index()

    fig = px.line(
        data,
        x="mes_de_referencia",
        y="volume_m3",
        markers=True,
        title="Movimentação Mensal do Terminal"
    )

    return fig


@app.callback(
    Output("grafico-produto-share","figure"),
    Input("grafico-produto-share","id")
)
def share(_):

    data = df.groupby("descricao_do_produto")["volume_m3"].sum().reset_index()

    fig = px.pie(
        data,
        values="volume_m3",
        names="descricao_do_produto",
        hole=0.4,
        title="Participação por Produto"
    )

    return fig


@app.callback(
    Output("grafico-operacao","figure"),
    Input("grafico-operacao","id")
)
def operacao(_):

    data = df.groupby("tipo_da_operacao")["volume_m3"].sum().reset_index()

    fig = px.bar(
        data,
        x="tipo_da_operacao",
        y="volume_m3",
        title="Volume por Tipo de Operação"
    )

    return fig


@app.callback(
    Output("grafico-transporte","figure"),
    Input("grafico-transporte","id")
)
def transporte(_):

    data = df.groupby(
        ["modo_de_transporte","descricao_do_produto"]
    )["volume_m3"].sum().reset_index()

    fig = px.bar(
        data,
        x="modo_de_transporte",
        y="volume_m3",
        color="descricao_do_produto",
        barmode="stack",
        title="Logística por Modal de Transporte"
    )

    return fig


@app.callback(
    Output("grafico-sazonal","figure"),
    Input("grafico-sazonal","id")
)
def sazonal(_):

    df_temp = df.copy()

    df_temp["ano"] = df_temp["mes_de_referencia"].dt.year
    df_temp["mes"] = df_temp["mes_de_referencia"].dt.month

    data = df_temp.groupby(["ano","mes"])["volume_m3"].sum().reset_index()

    fig = px.line(
        data,
        x="mes",
        y="volume_m3",
        color="ano",
        markers=True,
        title="Sazonalidade da Movimentação"
    )

    return fig


@app.callback(
    Output("grafico-ranking","figure"),
    Input("grafico-ranking","id")
)
def ranking(_):

    data = (
        df.groupby("descricao_do_produto")["volume_m3"]
        .sum()
        .reset_index()
        .sort_values("volume_m3",ascending=False)
    )

    fig = px.bar(
        data,
        x="descricao_do_produto",
        y="volume_m3",
        title="Ranking de Produtos"
    )

    return fig


# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":

    app.run_server(
        host="0.0.0.0",
        port=8050,
        debug=False
    )
