import pandas as pd

SHEET_ID = "119rDrAyWfXNEp70WdmgvA7OMEbbNX1wZ"
SHEET_NAME = "Dados"

URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

def load_data():

    # data atualização
    first_row = pd.read_csv(URL, nrows=1, header=None)

    data_atualizacao = first_row.iloc[0,1] if first_row.shape[1] > 1 else ""

    df = pd.read_csv(URL, skiprows=2)

    df.columns = df.columns.str.strip()

    # data
    df['mes_de_referencia'] = pd.to_datetime(df['mes_de_referencia'], errors='coerce')

    # volume seguro
    df["volume_m3"] = (
        df["volume_m3"]
        .astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )

    df["volume_m3"] = pd.to_numeric(df["volume_m3"], errors="coerce").fillna(0)

    # mapeamentos
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
        1:"Rodoviário",
        2:"Ferroviário",
        4:"Aquaviário",
        5:"Dutoviário",
        9:"Outros"
    })

    return df, data_atualizacao


import pandas as pd


def calculate_kpis(df):

    latest = df['mes_de_referencia'].max()

    previous = latest - pd.DateOffset(months=1)

    df_latest = df[df['mes_de_referencia'] == latest]

    df_prev = df[df['mes_de_referencia'] == previous]

    total_latest = df_latest['volume_m3'].sum()

    total_prev = df_prev['volume_m3'].sum()

    growth = ((total_latest-total_prev)/total_prev*100) if total_prev>0 else 0

    etanol = df[df['descricao_do_produto'].str.contains("ETANOL", na=False)]

    etanol_rec = etanol[etanol['sentido_da_operacao']=="Recepção"]['volume_m3'].sum()

    etanol_ent = etanol[etanol['sentido_da_operacao']=="Entrega"]['volume_m3'].sum()

    return {

        "latest_month": latest.strftime("%B/%Y"),

        "total_volume": total_latest,

        "growth_total": growth,

        "etanol_recebido": etanol_rec,

        "etanol_entregue": etanol_ent

    }



def monthly_timeseries(df):

    return df.groupby("mes_de_referencia")["volume_m3"].sum().reset_index()



def product_share(df):

    return df.groupby("descricao_do_produto")["volume_m3"].sum().reset_index()



def operation_type(df):

    return df.groupby("tipo_da_operacao")["volume_m3"].sum().reset_index()



def transport_matrix(df):

    return df.groupby(
        ["modo_de_transporte","descricao_do_produto"]
    )["volume_m3"].sum().reset_index()



def seasonal_analysis(df):

    df["ano"] = df["mes_de_referencia"].dt.year

    df["mes"] = df["mes_de_referencia"].dt.month

    return df.groupby(["ano","mes"])["volume_m3"].sum().reset_index()

import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
import plotly.express as px

def create_layout(df, data_atualizacao, kpis):

    return dbc.Container([

        # ------------------------------------------------
        # HEADER
        # ------------------------------------------------

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

        # ------------------------------------------------
        # KPI ROW
        # ------------------------------------------------

        dbc.Row([

            dbc.Col(dbc.Card([
                dbc.CardHeader("Volume Total Movimentado"),
                dbc.CardBody([
                    html.H2(
                        f"{kpis['total_volume']:,.0f} m³",
                        className="text-center"
                    )
                ])
            ], className="shadow-sm"), md=4),

            dbc.Col(dbc.Card([
                dbc.CardHeader("Etanol Recebido"),
                dbc.CardBody([
                    html.H2(
                        f"{kpis['etanol_recebido']:,.0f} m³",
                        className="text-center"
                    )
                ])
            ], className="shadow-sm"), md=4),

            dbc.Col(dbc.Card([
                dbc.CardHeader("Etanol Entregue"),
                dbc.CardBody([
                    html.H2(
                        f"{kpis['etanol_entregue']:,.0f} m³",
                        className="text-center"
                    )
                ])
            ], className="shadow-sm"), md=4),

        ], className="mb-4"),

        # ------------------------------------------------
        # MAIN TABS
        # ------------------------------------------------

        dbc.Tabs([

            # =================================================
            # ABA 1 — HISTÓRICO GERAL
            # =================================================

            dbc.Tab(label="Histórico Geral", children=[

                dbc.Row([

                    dbc.Col(
                        dcc.Graph(id="grafico-historico"),
                        lg=12
                    )

                ]),

                dbc.Row([

                    dbc.Col(
                        dcc.Graph(id="grafico-produto-share"),
                        lg=6
                    ),

                    dbc.Col(
                        dcc.Graph(id="grafico-operacao"),
                        lg=6
                    )

                ], className="mt-4")

            ]),

            # =================================================
            # ABA 2 — LOGÍSTICA
            # =================================================

            dbc.Tab(label="Logística", children=[

                dbc.Row([

                    dbc.Col(
                        dcc.Graph(id="grafico-transporte"),
                        lg=12
                    )

                ])

            ]),

            # =================================================
            # ABA 3 — SAZONALIDADE
            # =================================================

            dbc.Tab(label="Sazonalidade", children=[

                dbc.Row([

                    dbc.Col(
                        dcc.Graph(id="grafico-sazonal"),
                        lg=12
                    )

                ])

            ]),

            # =================================================
            # ABA 4 — RANKING PRODUTOS
            # =================================================

            dbc.Tab(label="Ranking Produtos", children=[

                dbc.Row([

                    dbc.Col(
                        dcc.Graph(id="grafico-ranking"),
                        lg=12
                    )

                ])

            ]),

            # =================================================
            # ABA 5 — DADOS COMPLETOS
            # =================================================

            dbc.Tab(label="Base de Dados", children=[

                dash_table.DataTable(

                    id="tabela-dados",

                    columns=[{"name": i, "id": i} for i in df.columns],

                    data=df.to_dict("records"),

                    page_size=20,

                    filter_action="native",

                    sort_action="native",

                    export_format="csv",

                    style_table={"overflowX":"auto"},

                    style_header={
                        "backgroundColor":"#2c3e50",
                        "color":"white",
                        "fontWeight":"bold"
                    },

                    style_cell={
                        "textAlign":"center",
                        "padding":"8px"
                    }

                )

            ])

        ])

    ], fluid=True)

from dash import Input, Output
import plotly.express as px
import pandas as pd

from analytics import (
    monthly_timeseries,
    product_share,
    operation_type,
    transport_matrix,
    seasonal_analysis
)

def register_callbacks(app, df):

    # HISTÓRICO

    @app.callback(
        Output("grafico-historico","figure"),
        Input("grafico-historico","id")
    )
    def historico(_):

        data = monthly_timeseries(df)

        fig = px.line(
            data,
            x="mes_de_referencia",
            y="volume_m3",
            markers=True,
            title="Movimentação Mensal do Terminal TECAB"
        )

        fig.update_layout(
            template="plotly_white",
            hovermode="x unified"
        )

        return fig


    # SHARE PRODUTO

    @app.callback(
        Output("grafico-produto-share","figure"),
        Input("grafico-produto-share","id")
    )
    def share(_):

        data = product_share(df)

        fig = px.pie(
            data,
            values="volume_m3",
            names="descricao_do_produto",
            hole=0.4,
            title="Participação por Produto"
        )

        return fig


    # TIPO OPERACAO

    @app.callback(
        Output("grafico-operacao","figure"),
        Input("grafico-operacao","id")
    )
    def operacao(_):

        data = operation_type(df)

        fig = px.bar(
            data,
            x="tipo_da_operacao",
            y="volume_m3",
            title="Volume por Tipo de Operação"
        )

        fig.update_layout(template="plotly_white")

        return fig


    # TRANSPORTE

    @app.callback(
        Output("grafico-transporte","figure"),
        Input("grafico-transporte","id")
    )
    def transporte(_):

        data = transport_matrix(df)

        fig = px.bar(
            data,
            x="modo_de_transporte",
            y="volume_m3",
            color="descricao_do_produto",
            barmode="stack",
            title="Logística por Modal de Transporte"
        )

        return fig


    # SAZONALIDADE

    @app.callback(
        Output("grafico-sazonal","figure"),
        Input("grafico-sazonal","id")
    )
    def sazonal(_):

        data = seasonal_analysis(df)

        fig = px.line(
            data,
            x="mes",
            y="volume_m3",
            color="ano",
            markers=True,
            title="Sazonalidade da Movimentação"
        )

        return fig


    # RANKING

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

import dash
import dash_bootstrap_components as dbc

from data_loader import load_data
from analytics import calculate_kpis
from layout import create_layout
from callbacks import register_callbacks


# ======================
# DATA
# ======================

df, data_atualizacao = load_data()

kpis = calculate_kpis(df)

# ======================
# APP
# ======================

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP]
)

server = app.server


# ======================
# LAYOUT
# ======================

app.layout = create_layout(
    df,
    data_atualizacao,
    kpis
)


# ======================
# CALLBACKS
# ======================

register_callbacks(app, df)


# ======================
# RUN
# ======================

if __name__ == "__main__":

    app.run_server(
        host="0.0.0.0",
        port=8050,
        debug=False
    )
