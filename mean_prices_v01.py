#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 27 22:10:16 2022

@author: hellano
"""

# Pacotes Básicos
import streamlit as st
import pandas as pd
import numpy as np

import io
import ast

# Leitura da Base no Google Sheet
import gspread
from google.oauth2 import service_account

# Web Scrapping
from requests_html import HTMLSession
from bs4 import BeautifulSoup

# Função para ler a planílha no Google Sheets
def leitor(credenciais, nome_planilha, nome_aba):
    
    # Permições para acessar google sheet
    gc = gspread.service_account_from_dict(credenciais)
    
    # Abrindo a planilha
    planilha = gc.open(nome_planilha).worksheet(nome_aba)
    
    # Lendo e transformando as informações em dataframe
    dados = planilha.get_all_records()
    df = pd.DataFrame(dados)
    
    return df

# Função converte as informações do arquivo .json em um dictionary
def json(file_upload):
    # To convert to a string based IO:
    stringio = io.StringIO(file_upload.getvalue().decode("utf-8"))

    # To read file as string:
    string_data = stringio.read()
    credenciais = ast.literal_eval(string_data)
    
    return credenciais

# Função para gravar informações no Google Sheets
def escritor(lista):
    # Permições para acessar google sheet
    gc = gspread.service_account_from_dict(credenciais)
    planilha = gc.open('Preço Ativos').worksheet('Página1')
    planilha.append_row(lista, value_input_option = 'USER_ENTERED')

# Função para calcular do preço médio do ativo
def mean_price():
    dados = leitor(credenciais, 'Preço Ativos', 'Página1')

    dados['Valor'] = dados['Valor']/100
    dados['Custo Total'] = dados['Custo Total']/100

    total = dados.groupby('Empresa')['Custo Total'].sum()
    quantidade = dados.groupby('Empresa')['Qtd'].sum()
    pmedio = pd.DataFrame({'Qtd':quantidade, 'Preço':total, 'Preço Médio':round(total/quantidade, 2)})
    pmedio = pmedio.query('Qtd != 0')
    
    return pmedio

# Função para fazer webscrap para pegar a cotação atual da ação no google
def indicador(ativo):
    k = list(empresas['Razao']).index(ativo)
    cotacao = empresas['Codigo'][k].lower()

    acesso = HTMLSession() # inicie um acesso (como se fosse um navegador)
    link = acesso.get('https://www.google.com/search?q=' + cotacao)

    html = BeautifulSoup(link.text, 'lxml')
    
    vatual = html.find('span', class_='IsqQVc NprOob wT3VGc')
    vatual = vatual.text.replace(',', '.')
    
    return(float(vatual))

@st.experimental_memo
def value_market():
    aux = list()
    
    for i in list(pmedio.index):
        aux.append(indicador(i))
        
    cotacaoAtualAtivos = pd.DataFrame({'Ativo':pmedio.index, 'Preço':aux})

    cotatual = sum(aux*pmedio['Qtd'])
    
    return cotatual, cotacaoAtualAtivos

# Função para coletar o preço atual do ativo
@st.experimental_memo
def price_today(ativo, pmedio):
    
    indece = list(valor_mercado[1]['Ativo']).index(ativo)
    cotacao = valor_mercado[1]['Preço'][indece]
    
    adiquirido = pmedio['Preço Médio'][ativo]
    qtda = pmedio.filter(items = [ativo], axis = 0)['Qtd']
    vinic = pmedio.filter(items = [ativo], axis = 0)['Preço']
    mercado = round(float(qtda*cotacao), 2)
    rent_ativo = round(100*(cotacao-adiquirido)/adiquirido, 2)
    rent_total = round(100*float((mercado - vinic)/vinic), 2)
    
    return cotacao, rent_ativo, mercado, rent_total

json_file = st.sidebar.file_uploader('Escolher credenciais')
if json_file is not None:
    
    credenciais = json(json_file)
    
    #### COLOCAR EM UMA FUNÇÃO ####

    file1 = '~/Documentos/Projetos Python/Projeto Preço Médio Ações/cod_açoes.csv'
    file2 = '~/Documentos/Projetos Python/Projeto Preço Médio Ações/cod_fiis.csv'
    file3 = '~/Documentos/Projetos Python/Projeto Preço Médio Ações/BDRs.csv'

    acao = pd.read_csv(file1, delimiter = ';')[['Codigo', 'Razao']]
    bdr = pd.read_csv(file3, delimiter = ';')[['Codigo', 'Razao']]
    fii = pd.read_csv(file2, delimiter = ';')[['Codigo', 'Razao']]
    fii['Codigo'] = fii['Codigo'] + '11'

    empresas = acao.append(fii)
    empresas = empresas.append(bdr)
    empresas = empresas.set_index(keys = np.array(list(range(len(empresas)))))
    codigo = empresas['Codigo'] + '-' + empresas['Razao']

    ####                      ####

    operacao = st.sidebar.selectbox('Tipo de Operação', ['Compra', 'Venda'], key = 'operacao')
    data = st.sidebar.date_input('Data da compra', key = 'data')
    nome = st.sidebar.selectbox('Nome do ativo', codigo, key = 'nome')

    nome = empresas['Razao'][list(codigo).index(nome)]

    valor = st.sidebar.number_input('Valor do ativo', min_value = 0.00, key = 'valor')
    qtd = st.sidebar.number_input('Quantidade comprada', min_value = 0, key = 'qtd')
    if operacao == 'Venda':
        qtd = -qtd
        valor = -valor
    taxa = st.sidebar.number_input('Taxas na compra', min_value = 0.00, key = 'taxa')

    custo = st.session_state.qtd*st.session_state.valor + st.session_state.taxa
    st.sidebar.number_input('Custo Total', value = custo, disabled = True)
    
    def get_clean():
        st.session_state.valor = 0.00
        st.session_state.qtd = 0
        st.session_state.taxa = 0.00
        
    if st.sidebar.button('Adicionar'):
        escritor([str(data), nome, valor, qtd, taxa, custo])
        
    st.sidebar.button('Limpar Campos', on_click = get_clean)
    
    pmedio = mean_price()

    st.header('Preço Médio por Ativo')

    col1, col2, col3 = st.columns([2, 1, 1])

    col1.dataframe(pmedio, width = 100000)

    investido = pmedio['Preço'].sum()
    col2.metric('Valor Investido', round(investido, 2))

    valor_mercado = value_market()

    rentabilidade = round(100*(valor_mercado[0] - investido)/investido, 2)

    col3.metric('Valor de Mercado', round(valor_mercado[0], 2), rentabilidade)
    
    st.header('Rentabilidade por Ativo')

    col1, col2, col3 = st.columns([2,1,1])

    ativo = col1.selectbox('Ativo', list(pmedio.index), key = 'ativo')

    cotacao, rent_ativo, mercado, rent_total = price_today(ativo, pmedio)

    col2.metric('Valor de Mercado:', cotacao, rent_ativo)
    col3.metric('Valor de Mercado: Total', mercado, rent_total)
