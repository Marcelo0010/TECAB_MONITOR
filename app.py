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

# --- Funções de Pré-processamento de Dados (CORRIGIDA PARA O RENDER) ---
def load_and_preprocess_data(url):
    # 1. Extrair data de atualização (primeira linha, célula B1)
    first_row = pd.read_csv(url, nrows=1, header=None)
    data_atualizacao = first_row.iloc[0, 1] if first_row.shape[1] > 1 else "Não informada"
    
    # 2. Carregar dados reais (pulando o cabeçalho descritivo do sheets)
    df = pd.read_csv(url, skiprows=2)
    df.columns = df.columns.str.strip()
    
    # 3. Mapear valores e Converter tipos de dados de forma segura
    df['mes_de_referencia'] = pd.to_datetime(df['mes_de_referencia'], format='%Y-%m', errors='coerce')
    
    # Tratamento da vírgula e conversão para float sem dar erro de "string"
    df["volume_m3"] = (
        df["volume_m3"]
        .astype(str)
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False)
    )
    df["volume_m3"] = pd.to_numeric(df["volume_m3"], errors='coerce').fillna(0)
    
    df["sentido_da_operacao"] = df["sentido_da_operacao"].map({1: "Recepção", 2: "Entrega"})
    
    df["tipo_da_operacao"] = df["tipo_da_operacao"].map({
        1: "Com armazenagem",
        2: "Sem armazenagem",
        3: "Transbordo",
        4: "Abastecimento",
        9: "Outros"
    })

    # Adicionando o modo de transporte para análises futuras
    df["modo_de_transporte"] = df["modo_de_transporte"].map({
        1: "Rodoviário", 2: "Ferroviário", 4: "Aquaviário", 5: "Dutoviário", 9: "Outros"
    })
    
    # 4. Filtrar etanol e outros produtos (Garantindo que é string antes de buscar)
    df_etanol = df[df["descricao_do_produto"].astype(str).str.contains("ETANOL", na=False)].copy()
    df_outros = df[~df["descricao_do_produto"].astype(str).str.contains("ETANOL", na=False)].copy()
    
    df_resumo_outros = df_outros.groupby(["mes_de_referencia", "descricao_do_produto", "sentido_da_operacao"])["volume_m3"].sum().reset_index()
    df_resumo_outros = df_resumo_outros.sort_values(by="mes_de_referencia", ascending=False)
    
    return df, data_atualizacao, df_etanol, df_resumo_outros

# Carregar dados
df, data_atualizacao, df_etanol, df_resumo_outros = load_and_preprocess_data(URL)

# --- Cálculos para KPIs (SEU CÓDIGO ORIGINAL INTACTO) ---
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
    etanol_recepcao_latest = df_latest[df_latest["descricao_do_produto"].astype(str).str.contains("ETANOL", na=False) & 
                                     (df_latest["sentido_da_operacao"] == "Recepção")]['volume_m3'].sum()
    
    etanol_recepcao_previous = df_previous[df_previous["descricao_do_produto"].astype(str).str.contains("ETANOL", na=False) & 
                                           (df_previous["sentido_da_operacao"] == "Recepção")]['volume_m3'].sum()
    
    etanol_entrega_latest = df_latest[df_latest["descricao_do_produto"].astype(str).str.contains("ETANOL", na=False) & 
                                    (df_latest["sentido_da_operacao"] == "Entrega")]['volume_m3'].sum()
    
    etanol_entrega_previous = df_previous[df_previous["descricao_do_produto"].astype(str).str.contains("ETANOL", na=False) & 
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
server = app.server  

# Layout do aplicativo
app.layout = dbc.Container(
    fluid=True,
    style={
        'backgroundColor': '#f8f9fa',
        'padding': '20px',
        'minHeight': '100vh',
    },
    children=[
        # TÍTULO
        html.H1(
            "Dashboard de Movimentação de Combustíveis",
            className="text-center my-3"
        ),

        # DATA DE ATUALIZAÇÃO
        html.H6(
            f"Última atualização: {data_atualizacao}",
            className="text-center text-muted mb-1"
        ),

        # MÊS DE REFERÊNCIA
        html.H6(
            f"Mês de referência: {kpis['latest_month']}",
            className="text-center text-muted mb-3"
        ),

        html.Hr(),
    
        # Seção de KPIs (SEU CÓDIGO ORIGINAL)
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Volume Total Movimentado (m³)", className="fw-bold"),
                dbc.CardBody([
                    html.H2(f"{kpis['total_volume']:,.2f}", className="card-title text-center mb-1"),
                    html.P([
                        f"{kpis['latest_month']} | ",
                        html.Span(f"{kpis['growth_total']:+.2f}%", className="text-success" if kpis['growth_total'] >= 0 else "text-danger"),
                        html.Span(" ▲" if kpis['growth_total'] >= 0 else " ▼", className="text-success" if kpis['growth_total'] >= 0 else "text-danger")
                    ], className="card-text text-center mb-0")
                ])
            ], className="shadow-sm h-100"), md=4),
            
            dbc.Col(dbc.Card([
                dbc.CardHeader("Etanol Recebido (m³)", className="fw-bold"),
                dbc.CardBody([
                    html.H2(f"{kpis['etanol_recepcao']:,.2f}", className="card-title text-center mb-1"),
                    html.P([
                        f"{kpis['latest_month']} | ",
                        html.Span(f"{kpis['growth_recepcao']:+.2f}%", className="text-success" if kpis['growth_recepcao'] >= 0 else "text-danger"),
                        html.Span(" ▲" if kpis['growth_recepcao'] >= 0 else " ▼", className="text-success" if kpis['growth_recepcao'] >= 0 else "text-danger")
                    ], className="card-text text-center mb-0")
                ])
            ], className="shadow-sm h-100"), md=4),
            
            dbc.Col(dbc.Card([
                dbc.CardHeader("Etanol Entregue (m³)", className="fw-bold"),
                dbc.CardBody([
                    html.H2(f"{kpis['etanol_entrega']:,.2f}", className="card-title text-center mb-1"),
                    html.P([
                        f"{kpis['latest_month']} | ",
                        html.Span(f"{kpis['growth_entrega']:+.2f}%", className="text-success" if kpis['growth_entrega'] >= 0 else "text-danger"),
                        html.Span(" ▲" if kpis['growth_entrega'] >= 0 else " ▼", className="text-success" if kpis['growth_entrega'] >= 0 else "text-danger")
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
                                    # Adicionado "TODOS" para que o gráfico de pizza faça sentido
                                    options=[{"label": "TODOS OS PRODUTOS", "value": "TODOS"}] + 
                                            [{"label": prod, "value": prod} for prod in sorted(df["descricao_do_produto"].unique())],
                                    value="TODOS",
                                    clearable=False,
                                    className="mb-3"
                                ),
                            ], md=4),
                            
                            dbc.Col([
                                html.Label("Selecione o Tipo de Operação:", className="fw-bold"),
                                dcc.Dropdown(
                                    id="dropdown-tipo-operacao",
                                    options=[{"label": tipo, "value": tipo} for tipo in df["tipo_da_operacao"].dropna().unique()],
                                    value="Com armazenagem",
                                    clearable=False,
                                    className="mb-3"
                                ),
                            ], md=4),
                            
                            dbc.Col([
                                html.Label("Selecione o Sentido da Operação:", className="fw-bold"),
                                dcc.Dropdown(
                                    id="dropdown-sentido-operacao",
                                    options=[{"label": sentido, "value": sentido} for sentido in df["sentido_da_operacao"].dropna().unique()],
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
                                    marks={int(x): f'{int(x):,}' for x in np.linspace(df['volume_m3'].min(), df['volume_m3'].max(), 5)},
                                    tooltip={"placement": "bottom", "always_visible": True},
                                    className="mb-4"
                                ),
                            ], width=12),
                        ]),
                        
                        # Gráficos (OS SEUS 3 GRÁFICOS ORIGINAIS)
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
                                    style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'},
                                    style_cell={'textAlign': 'center', 'padding': '10px', 'border': '1px solid #dee2e6'},
                                    style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
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
                            style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'},
                            style_cell={'textAlign': 'center', 'padding': '10px', 'border': '1px solid #dee2e6'},
                            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
                            page_size=15,
                            export_format="csv",
                        )
                    ])
                ], className="mt-3 shadow")
            ]),

            # Tab 4: Sazonalidade (Bônus adicionado)
            dbc.Tab(label="Sazonalidade Histórica", tab_id="tab-sazonalidade", children=[
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Comparativo Anual por Produto", className="mb-4"),
                        dcc.Dropdown(
                            id="dropdown-sazonal",
                            options=[{"label": prod, "value": prod} for prod in sorted(df["descricao_do_produto"].unique())],
                            value="ETANOL ANIDRO",
                            clearable=False,
                            className="mb-4"
                        ),
                        dcc.Graph(id="grafico-sazonalidade", className="shadow-sm")
                    ])
                ], className="mt-3 shadow")
            ]),
            
        ], id="main-tabs", active_tab="tab-etanol-overview"),
        
        # Armazenamento de dados filtrados
        dcc.Store(id='filtered-data-store')
    ]
)

# --- Callbacks ---

# Atualizar gráficos de etanol com base no período selecionado
@app.callback(
    [Output("graph-etanol-recebido", "figure"), Output("graph-etanol-entregue", "figure")],
    [Input("date-range-etanol", "start_date"), Input("date-range-etanol", "end_date")]
)
def update_etanol_graphs(start_date, end_date):
    if not start_date or not end_date:
        return px.scatter(title="Selecione um período válido"), px.scatter(title="Selecione um período válido")
    
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    filtered_df = df_etanol[(df_etanol['mes_de_referencia'] >= start_date) & (df_etanol['mes_de_referencia'] <= end_date)]
    
    df_recebido = filtered_df[filtered_df["sentido_da_operacao"] == "Recepção"].groupby("mes_de_referencia")["volume_m3"].sum().reset_index()
    df_entregue = filtered_df[filtered_df["sentido_da_operacao"] == "Entrega"].groupby("mes_de_referencia")["volume_m3"].sum().reset_index()
    
    fig_recebido = px.line(df_recebido, x="mes_de_referencia", y="volume_m3", title="Volume de Etanol Recebido (m³)", markers=True)
    fig_recebido.update_layout(hovermode="x unified", xaxis_title=None, yaxis_title="Volume (m³)", template="plotly_white")
    
    fig_entregue = px.line(df_entregue, x="mes_de_referencia", y="volume_m3", title="Volume de Etanol Entregue (m³)", markers=True)
    fig_entregue.update_layout(hovermode="x unified", xaxis_title=None, yaxis_title="Volume (m³)", template="plotly_white")
    
    return fig_recebido, fig_entregue

# Armazenar dados filtrados (SEU CÓDIGO ORIGINAL)
@app.callback(
    Output('filtered-data-store', 'data'),
    [Input("dropdown-produto", "value"),
     Input("dropdown-tipo-operacao", "value"),
     Input("dropdown-sentido-operacao", "value"),
     Input("range-slider-volume", "value")]
)
def store_filtered_data(produto, tipo_operacao, sentido_operacao, volume_range):
    min_volume, max_volume = volume_range
    
    # Condição para permitir visualizar a distribuição de todos os produtos
    if produto == "TODOS":
        filtered_df = df[
            (df["tipo_da_operacao"] == tipo_operacao) &
            (df["sentido_da_operacao"] == sentido_operacao) &
            (df["volume_m3"] >= min_volume) &
            (df["volume_m3"] <= max_volume)
        ]
    else:
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
    [Output("grafico-tipo-operacao", "figure"), Output("tabela-tipo-operacao", "data")],
    [Input("filtered-data-store", "data")]
)
def update_tipo_operacao_graph_and_table(stored_data):
    if not stored_data:
        return px.scatter(title="Nenhum dado encontrado com os filtros selecionados"), []
    
    filtered_df = pd.DataFrame(stored_data)
    grouped_df = filtered_df.groupby("mes_de_referencia")["volume_m3"].sum().reset_index()
    
    fig = px.bar(grouped_df, x="mes_de_referencia", y="volume_m3", title="Volume por Mês de Referência", color_discrete_sequence=['#3498db'])
    fig.update_layout(hovermode="x unified", xaxis_title=None, yaxis_title="Volume (m³)", template="plotly_white")
    
    return fig, grouped_df.to_dict("records")

# Atualizar gráfico de distribuição de produtos
@app.callback(
    Output("grafico-distribuicao-produto", "figure"),
    [Input("filtered-data-store", "data")]
)
def update_product_distribution_pie(stored_data):
    if not stored_data:
        return px.scatter(title="Nenhum dado encontrado")
    
    filtered_df = pd.DataFrame(stored_data)
    product_distribution = filtered_df.groupby("descricao_do_produto")["volume_m3"].sum().reset_index()
    
    fig = px.pie(product_distribution, values='volume_m3', names='descricao_do_produto', title='Distribuição de Volume por Produto', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
    fig.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#000000', width=0.5)))
    fig.update_layout(uniformtext_minsize=10, uniformtext_mode='hide', showlegend=False)
    
    return fig

# Atualizar gráfico de barras empilhadas
@app.callback(
    Output("grafico-barras-empilhadas", "figure"),
    [Input("filtered-data-store", "data")]
)
def update_stacked_bar_chart(stored_data):
    if not stored_data:
        return px.scatter(title="Nenhum dado encontrado")
    
    filtered_df = pd.DataFrame(stored_data)
    stacked_data = filtered_df.groupby(["mes_de_referencia", "tipo_da_operacao"])["volume_m3"].sum().reset_index()
    
    fig = px.bar(stacked_data, x="mes_de_referencia", y="volume_m3", color="tipo_da_operacao", title="Volume por Tipo de Operação", barmode='stack', color_discrete_sequence=px.colors.qualitative.Pastel)
    fig.update_layout(hovermode="x unified", xaxis_title=None, yaxis_title="Volume (m³)", template="plotly_white", legend_title_text='Tipo de Operação')
    
    return fig

# Callback para a aba bônus de Sazonalidade
@app.callback(
    Output("grafico-sazonalidade", "figure"),
    [Input("dropdown-sazonal", "value")]
)
def update_seasonal_graph(prod):
    dff = df[df["descricao_do_produto"] == prod].copy()
    dff['ano'] = dff['mes_de_referencia'].dt.year
    dff['mes'] = dff['mes_de_referencia'].dt.month
    
    seasonal = dff.groupby(['ano', 'mes'])['volume_m3'].sum().reset_index()
    fig = px.line(seasonal, x='mes', y='volume_m3', color='ano', title=f"Sazonalidade: {prod}", markers=True)
    fig.update_layout(xaxis=dict(tickmode='linear', tick0=1, dtick=1), template="plotly_white", xaxis_title="Mês do Ano", yaxis_title="Volume (m³)")
    return fig

if __name__ == "__main__":
    app.run_server(debug=True, port=8050)
if __name__ == "__main__":
    app.run_server(debug=True, port=8050)
    

