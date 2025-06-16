import pandas as pd
import dash
from dash import dcc, html, dash_table, Input, Output, State
import plotly.express as px
import dash_bootstrap_components as dbc
from datetime import datetime
import numpy as np

# URL do Google Sheets (compartilhado publicamente como CSV)
SHEET_ID = "119rDrAyWfXNEp70WdmgvA7OMEbbNX1wZ"
SHEET_NAME = "Dados"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

# --- Funções de Pré-processamento de Dados ---
def load_and_preprocess_data(url):
    # Carregar dados
    df = pd.read_csv(url, skiprows=0)
    
    # Extrair data de atualização (primeira linha)
    first_row = pd.read_csv(url, nrows=1, header=None)
    data_atualizacao = first_row.iloc[0, 0]
    
    # Renomear colunas
    df.rename(columns={
        "Atualizado em: mes_de_referencia": "mes_de_referencia",
        "Histórico dos volumes mensais movimentados no terminal  Em atendimento ao artigo 26, III, d, da Resolução ANP nº 881, de 8 de julho de 2022 nome_do_terminal": "nome_terminal"
    }, inplace=True)
    
    # Mapear valores
    df["sentido_da_operacao"] = df["sentido_da_operacao"].map({1: "Recepção", 2: "Entrega"})
    
    # Converter tipos de dados
    df['mes_de_referencia'] = pd.to_datetime(df['mes_de_referencia'], format='%Y-%m', errors='coerce')
    df.loc[:, "volume_m3"] = df["volume_m3"].astype(str).str.replace(',', '.').astype(float)
    
    # Mapear tipo de operação
    df["tipo_da_operacao"] = df["tipo_da_operacao"].map({
        1: "Com armazenagem",
        2: "Sem armazenagem",
        3: "Transbordo",
        4: "Abastecimento",
        9: "Outros"
    })
    
    # Filtrar etanol e outros produtos
    df_etanol = df[df["descricao_do_produto"].str.contains("ETANOL", na=False)]
    
    df_outros = df[~df["descricao_do_produto"].str.contains("ETANOL", na=False)]
    df_resumo_outros = df_outros.groupby(["mes_de_referencia", "descricao_do_produto", "sentido_da_operacao"])["volume_m3"].sum().reset_index()
    df_resumo_outros = df_resumo_outros.sort_values(by="mes_de_referencia", ascending=False)
    
    return df, data_atualizacao, df_etanol, df_resumo_outros

# Carregar dados
df, data_atualizacao, df_etanol, df_resumo_outros = load_and_preprocess_data(URL)

# --- Cálculos para KPIs ---
def calculate_kpis(df_data):
    # Encontrar meses mais recentes
    latest_month = df_data['mes_de_referencia'].max()
    previous_month = latest_month - pd.DateOffset(months=1)
    
    # Filtrar dados dos últimos meses
    df_latest = df_data[df_data['mes_de_referencia'] == latest_month]
    df_previous = df_data[df_data['mes_de_referencia'] == previous_month]
    
    # Calcular volumes totais
    total_volume_latest = df_latest['volume_m3'].sum()
    total_volume_previous = df_previous['volume_m3'].sum()
    
    # Calcular volumes de etanol
    etanol_recepcao_latest = df_latest[df_latest["descricao_do_produto"].str.contains("ETANOL", na=False) & 
                                     (df_latest["sentido_da_operacao"] == "Recepção")]['volume_m3'].sum()
    
    etanol_recepcao_previous = df_previous[df_previous["descricao_do_produto"].str.contains("ETANOL", na=False) & 
                                           (df_previous["sentido_da_operacao"] == "Recepção")]['volume_m3'].sum()
    
    etanol_entrega_latest = df_latest[df_latest["descricao_do_produto"].str.contains("ETANOL", na=False) & 
                                    (df_latest["sentido_da_operacao"] == "Entrega")]['volume_m3'].sum()
    
    etanol_entrega_previous = df_previous[df_previous["descricao_do_produto"].str.contains("ETANOL", na=False) & 
                                          (df_previous["sentido_da_operacao"] == "Entrega")]['volume_m3'].sum()
    
    # Calcular taxas de crescimento
    growth_total = ((total_volume_latest - total_volume_previous) / total_volume_previous * 100) if total_volume_previous > 0 else 0
    growth_recepcao = ((etanol_recepcao_latest - etanol_recepcao_previous) / etanol_recepcao_previous * 100) if etanol_recepcao_previous > 0 else 0
    growth_entrega = ((etanol_entrega_latest - etanol_entrega_previous) / etanol_entrega_previous * 100) if etanol_entrega_previous > 0 else 0

    return {
        'total_volume': total_volume_latest,
        'growth_total': growth_total,
        'etanol_recepcao': etanol_recepcao_latest,
        'growth_recepcao': growth_recepcao,
        'etanol_entrega': etanol_entrega_latest,
        'growth_entrega': growth_entrega,
        'latest_month': latest_month.strftime('%B/%Y')
    }

# Calcular KPIs
kpis = calculate_kpis(df)

# --- Configuração do Dash App ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Dashboard de Movimentação de Combustíveis"

# Layout do aplicativo


app.layout = dbc.Container(fluid=True,style={
        'backgroundColor': '#f8f9fa',  # Cinza claro (você pode usar cores hex, RGB ou nomes)
        'padding': '20px',
        'minHeight': '100vh',  # Garante que o fundo cubra toda a tela
    }, children=[
    # Cabeçalho com data de atualização
    dbc.Row(
        dbc.Col(
            html.H4(f"Última atualização: {data_atualizacao}", 
                    className="text-end text-muted my-2"),
            width={"size": 4, "offset": 8}
        )
    ),
    
    html.Hr(),
    
    # Seção de KPIs
    dbc.Row([
        # KPI 1: Volume Total
        dbc.Col(dbc.Card([
            dbc.CardHeader("Volume Total Movimentado (m³)", className="fw-bold"),
            dbc.CardBody([
                html.H2(f"{kpis['total_volume']:,.2f}", className="card-title text-center mb-1"),
                html.P([
                    f"{kpis['latest_month']} | ",
                    html.Span(f"{kpis['growth_total']:+.2f}%", 
                              className="text-success" if kpis['growth_total'] >= 0 else "text-danger"),
                    html.Span(" ▲" if kpis['growth_total'] >= 0 else " ▼", 
                              className="text-success" if kpis['growth_total'] >= 0 else "text-danger")
                ], className="card-text text-center mb-0")
            ])
        ], className="shadow-sm h-100"), md=4),
        
        # KPI 2: Etanol Recebido
        dbc.Col(dbc.Card([
            dbc.CardHeader("Etanol Recebido (m³)", className="fw-bold"),
            dbc.CardBody([
                html.H2(f"{kpis['etanol_recepcao']:,.2f}", className="card-title text-center mb-1"),
                html.P([
                    f"{kpis['latest_month']} | ",
                    html.Span(f"{kpis['growth_recepcao']:+.2f}%", 
                              className="text-success" if kpis['growth_recepcao'] >= 0 else "text-danger"),
                    html.Span(" ▲" if kpis['growth_recepcao'] >= 0 else " ▼", 
                              className="text-success" if kpis['growth_recepcao'] >= 0 else "text-danger")
                ], className="card-text text-center mb-0")
            ])
        ], className="shadow-sm h-100"), md=4),
        
        # KPI 3: Etanol Entregue
        dbc.Col(dbc.Card([
            dbc.CardHeader("Etanol Entregue (m³)", className="fw-bold"),
            dbc.CardBody([
                html.H2(f"{kpis['etanol_entrega']:,.2f}", className="card-title text-center mb-1"),
                html.P([
                    f"{kpis['latest_month']} | ",
                    html.Span(f"{kpis['growth_entrega']:+.2f}%", 
                              className="text-success" if kpis['growth_entrega'] >= 0 else "text-danger"),
                    html.Span(" ▲" if kpis['growth_entrega'] >= 0 else " ▼", 
                              className="text-success" if kpis['growth_entrega'] >= 0 else "text-danger")
                ], className="card-text text-center mb-0")
            ])
        ], className="shadow-sm h-100"), md=4),
    ], className="mb-4 g-3"),
    
    # Abas Principais
    dbc.Tabs([
        # Tab 1: Visão Geral do Etanol
        dbc.Tab(label="Visão Geral Etanol", tab_id="tab-etanol-overview", children=[
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Selecione o Período:", className="fw-bold mb-2"),
                            dcc.DatePickerRange(
                                id='date-range-etanol',
                                min_date_allowed=df_etanol['mes_de_referencia'].min(),
                                max_date_allowed=df_etanol['mes_de_referencia'].max(),
                                start_date=df_etanol['mes_de_referencia'].min(),
                                end_date=df_etanol['mes_de_referencia'].max(),
                                display_format='DD/MM/YYYY',
                                className="mb-4"
                            ),
                        ], md=6),
                    ]),
                    dbc.Row([
                        dbc.Col(dcc.Graph(id="graph-etanol-recebido", className="shadow-sm"), lg=6),
                        dbc.Col(dcc.Graph(id="graph-etanol-entregue", className="shadow-sm"), lg=6),
                    ], className="g-3")
                ])
            ], className="mt-3 shadow")
        ]),
        
        # Tab 2: Análise Detalhada
        dbc.Tab(label="Análise Detalhada", tab_id="tab-detailed-analysis", children=[
            dbc.Card([
                dbc.CardBody([
                    # Filtros
                    dbc.Row([
                        dbc.Col([
                            html.Label("Selecione o Produto:", className="fw-bold"),
                            dcc.Dropdown(
                                id="dropdown-produto",
                                options=[{"label": prod, "value": prod} for prod in sorted(df["descricao_do_produto"].unique())],
                                value="ETANOL",
                                clearable=False,
                                className="mb-3"
                            ),
                        ], md=4),
                        
                        dbc.Col([
                            html.Label("Selecione o Tipo de Operação:", className="fw-bold"),
                            dcc.Dropdown(
                                id="dropdown-tipo-operacao",
                                options=[{"label": tipo, "value": tipo} for tipo in df["tipo_da_operacao"].unique()],
                                value="Com armazenagem",
                                clearable=False,
                                className="mb-3"
                            ),
                        ], md=4),
                        
                        dbc.Col([
                            html.Label("Selecione o Sentido da Operação:", className="fw-bold"),
                            dcc.Dropdown(
                                id="dropdown-sentido-operacao",
                                options=[{"label": sentido, "value": sentido} for sentido in df["sentido_da_operacao"].unique()],
                                value="Recepção",
                                clearable=False,
                                className="mb-3"
                            ),
                        ], md=4),
                    ], className="g-3 mb-4"),
                    
                    # Slider de Volume
                    dbc.Row([
                        dbc.Col([
                            html.Label("Selecione o Intervalo de Volume (m³):", className="fw-bold"),
                            dcc.RangeSlider(
                                id='range-slider-volume',
                                min=df['volume_m3'].min(),
                                max=df['volume_m3'].max(),
                                step=1000,
                                value=[df['volume_m3'].min(), df['volume_m3'].max()],
                                marks={int(x): f'{int(x):,}' for x in np.linspace(
                                    df['volume_m3'].min(), 
                                    df['volume_m3'].max(), 
                                    5
                                )},
                                tooltip={"placement": "bottom", "always_visible": True},
                                className="mb-4"
                            ),
                        ], width=12),
                    ]),
                    
                    # Gráficos
                    dbc.Row([
                        dbc.Col(dcc.Graph(id="grafico-tipo-operacao", className="shadow-sm"), lg=6),
                        dbc.Col(dcc.Graph(id="grafico-distribuicao-produto", className="shadow-sm"), lg=6),
                    ], className="g-3 mb-4"),
                    
                    dbc.Row([
                        dbc.Col(dcc.Graph(id="grafico-barras-empilhadas", className="shadow-sm"), width=12),
                    ], className="mb-4"),
                    
                    # Tabela
                    dbc.Row([
                        dbc.Col([
                            html.H5("Dados Detalhados", className="mb-3"),
                            dash_table.DataTable(
                                id="tabela-tipo-operacao",
                                columns=[
                                    {"name": "Mês", "id": "mes_de_referencia", "type": "datetime"},
                                    {"name": "Volume (m³)", "id": "volume_m3", "type": "numeric", "format": dash_table.Format.Format(precision=2, scheme=dash_table.Format.Scheme.fixed)}
                                ],
                                style_table={'overflowX': 'auto', 'borderRadius': '8px'},
                                style_header={
                                    'backgroundColor': '#2c3e50',
                                    'color': 'white',
                                    'fontWeight': 'bold'
                                },
                                style_cell={
                                    'textAlign': 'center',
                                    'padding': '10px',
                                    'border': '1px solid #dee2e6'
                                },
                                style_data_conditional=[
                                    {
                                        'if': {'row_index': 'odd'},
                                        'backgroundColor': 'rgb(248, 248, 248)'
                                    }
                                ],
                                page_size=10,
                                export_format="csv",
                            )
                        ], width=12),
                    ])
                ])
            ], className="mt-3 shadow")
        ]),
        
        # Tab 3: Resumo de Outros Produtos
        dbc.Tab(label="Resumo Outros Produtos", tab_id="tab-outros-produtos", children=[
            dbc.Card([
                dbc.CardBody([
                    html.H5("Resumo de Outros Produtos", className="mb-4"),
                    dash_table.DataTable(
                        id='tabela-outros-produtos',
                        columns=[{"name": i, "id": i} for i in df_resumo_outros.columns],
                        data=df_resumo_outros.to_dict("records"),
                        style_table={'overflowX': 'auto', 'borderRadius': '8px'},
                        style_header={
                            'backgroundColor': '#2c3e50',
                            'color': 'white',
                            'fontWeight': 'bold'
                        },
                        style_cell={
                            'textAlign': 'center',
                            'padding': '10px',
                            'border': '1px solid #dee2e6'
                        },
                        style_data_conditional=[
                            {
                                'if': {'row_index': 'odd'},
                                'backgroundColor': 'rgb(248, 248, 248)'
                            }
                        ],
                        page_size=15,
                        export_format="csv",
                    )
                ])
            ], className="mt-3 shadow")
        ]),
    ], id="main-tabs", active_tab="tab-etanol-overview"),
    
    # Armazenamento de dados filtrados
    dcc.Store(id='filtered-data-store')
])

# --- Callbacks ---

# Atualizar gráficos de etanol com base no período selecionado
@app.callback(
    [Output("graph-etanol-recebido", "figure"),
     Output("graph-etanol-entregue", "figure")],
    [Input("date-range-etanol", "start_date"),
     Input("date-range-etanol", "end_date")]
)
def update_etanol_graphs(start_date, end_date):
    if not start_date or not end_date:
        return px.scatter(title="Selecione um período válido"), px.scatter(title="Selecione um período válido")
    
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    # Filtrar dados
    filtered_df = df_etanol[
        (df_etanol['mes_de_referencia'] >= start_date) & 
        (df_etanol['mes_de_referencia'] <= end_date)
    ]
    
    # Preparar dados para gráficos
    df_recebido = filtered_df[filtered_df["sentido_da_operacao"] == "Recepção"]
    df_recebido = df_recebido.groupby("mes_de_referencia")["volume_m3"].sum().reset_index()
    
    df_entregue = filtered_df[filtered_df["sentido_da_operacao"] == "Entrega"]
    df_entregue = df_entregue.groupby("mes_de_referencia")["volume_m3"].sum().reset_index()
    
    # Criar gráficos
    fig_recebido = px.line(
        df_recebido, 
        x="mes_de_referencia", 
        y="volume_m3",
        title="Volume de Etanol Recebido (m³)",
        labels={"mes_de_referencia": "Mês", "volume_m3": "Volume (m³)"},
        markers=True
    )
    fig_recebido.update_layout(
        hovermode="x unified",
        xaxis_title=None,
        yaxis_title="Volume (m³)",
        template="plotly_white"
    )
    
    fig_entregue = px.line(
        df_entregue, 
        x="mes_de_referencia", 
        y="volume_m3",
        title="Volume de Etanol Entregue (m³)",
        labels={"mes_de_referencia": "Mês", "volume_m3": "Volume (m³)"},
        markers=True
    )
    fig_entregue.update_layout(
        hovermode="x unified",
        xaxis_title=None,
        yaxis_title="Volume (m³)",
        template="plotly_white"
    )
    
    return fig_recebido, fig_entregue

# Armazenar dados filtrados
@app.callback(
    Output('filtered-data-store', 'data'),
    [Input("dropdown-produto", "value"),
     Input("dropdown-tipo-operacao", "value"),
     Input("dropdown-sentido-operacao", "value"),
     Input("range-slider-volume", "value")]
)
def store_filtered_data(produto, tipo_operacao, sentido_operacao, volume_range):
    min_volume, max_volume = volume_range
    
    filtered_df = df[
        (df["descricao_do_produto"] == produto) &
        (df["tipo_da_operacao"] == tipo_operacao) &
        (df["sentido_da_operacao"] == sentido_operacao) &
        (df["volume_m3"] >= min_volume) &
        (df["volume_m3"] <= max_volume)
    ]
    
    return filtered_df.to_dict('records')

# Atualizar gráfico de tipo de operação e tabela
@app.callback(
    [Output("grafico-tipo-operacao", "figure"),
     Output("tabela-tipo-operacao", "data")],
    [Input("filtered-data-store", "data")]
)
def update_tipo_operacao_graph_and_table(stored_data):
    if stored_data is None:
        return px.scatter(title="Selecione filtros válidos"), []
    
    filtered_df = pd.DataFrame(stored_data)
    if filtered_df.empty:
        return px.scatter(title="Nenhum dado encontrado com os filtros selecionados"), []
    
    # Preparar dados para gráfico e tabela
    grouped_df = filtered_df.groupby("mes_de_referencia")["volume_m3"].sum().reset_index()
    
    # Criar gráfico de barras
    fig = px.bar(
        grouped_df, 
        x="mes_de_referencia", 
        y="volume_m3",
        title="Volume por Mês de Referência",
        labels={"mes_de_referencia": "Mês", "volume_m3": "Volume (m³)"},
        color_discrete_sequence=['#3498db']
    )
    fig.update_layout(
        hovermode="x unified",
        xaxis_title=None,
        yaxis_title="Volume (m³)",
        template="plotly_white"
    )
    
    # Preparar dados da tabela
    table_data = grouped_df.to_dict("records")
    
    return fig, table_data

# Atualizar gráfico de distribuição de produtos
@app.callback(
    Output("grafico-distribuicao-produto", "figure"),
    [Input("filtered-data-store", "data")]
)
def update_product_distribution_pie(stored_data):
    if stored_data is None:
        return px.scatter(title="Selecione filtros válidos")
    
    filtered_df = pd.DataFrame(stored_data)
    if filtered_df.empty:
        return px.scatter(title="Nenhum dado encontrado com os filtros selecionados")
    
    # Agregar dados para gráfico de pizza
    product_distribution = filtered_df.groupby("descricao_do_produto")["volume_m3"].sum().reset_index()
    
    fig = px.pie(
        product_distribution, 
        values='volume_m3', 
        names='descricao_do_produto',
        title='Distribuição de Volume por Produto',
        hole=0.4,
        labels={"descricao_do_produto": "Produto", "volume_m3": "Volume (m³)"},
        color_discrete_sequence=px.colors.qualitative.Pastel,
        hover_data=['volume_m3']
    )
    fig.update_traces(
        textposition='inside', 
        textinfo='percent+label',
        marker=dict(line=dict(color='#000000', width=0.5))
    )
    fig.update_layout(
        uniformtext_minsize=10, 
        uniformtext_mode='hide',
        showlegend=False
    )
    
    return fig

# Atualizar gráfico de barras empilhadas
@app.callback(
    Output("grafico-barras-empilhadas", "figure"),
    [Input("filtered-data-store", "data")]
)
def update_stacked_bar_chart(stored_data):
    if stored_data is None:
        return px.scatter(title="Selecione filtros válidos")
    
    filtered_df = pd.DataFrame(stored_data)
    if filtered_df.empty:
        return px.scatter(title="Nenhum dado encontrado com os filtros selecionados")
    
    # Agregar dados para gráfico empilhado
    stacked_data = filtered_df.groupby(["mes_de_referencia", "tipo_da_operacao"])["volume_m3"].sum().reset_index()
    
    fig = px.bar(
        stacked_data, 
        x="mes_de_referencia", 
        y="volume_m3", 
        color="tipo_da_operacao",
        title="Volume por Tipo de Operação",
        labels={"mes_de_referencia": "Mês", "volume_m3": "Volume (m³)", "tipo_da_operacao": "Tipo de Operação"},
        barmode='stack',
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig.update_layout(
        hovermode="x unified",
        xaxis_title=None,
        yaxis_title="Volume (m³)",
        template="plotly_white",
        legend_title_text='Tipo de Operação'
    )
    
    return fig



if __name__ == "__main__":
    app.run_server(debug=False)
    
