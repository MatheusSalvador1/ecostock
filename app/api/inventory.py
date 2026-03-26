"""
Blueprint: Inventário
- Controle de entradas, saídas e descartes
- FIFO real por produto (ignorando vencidos)
- Histórico de movimentações com valores
- Alertas de validade, perdas e estoque baixo
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from app.services.auditoria import registrar
from app.utils.db import execute, query

inventory_bp = Blueprint('inventory', __name__)


ZERO = Decimal('0')


def _to_decimal(value, default: str = '0') -> Decimal:
    raw = str(value if value is not None and value != '' else default).replace(',', '.').strip()
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        return Decimal(default)



def _parse_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.strptime(text[:10], '%Y-%m-%d').date()
    except ValueError:
        return None



def _lote_vencido(row: dict) -> bool:
    validade = _parse_date(row.get('data_validade'))
    return bool(validade and validade < date.today())



def _status_lote(dias_restantes: int | None) -> str:
    if dias_restantes is None:
        return 'Sem validade'
    if dias_restantes < 0:
        return 'VENCIDO'
    if dias_restantes <= 7:
        return 'Crítico'
    if dias_restantes <= 15:
        return 'Alerta'
    if dias_restantes <= 30:
        return 'Aviso'
    return 'Normal'



def _serializar_lote(row: dict) -> dict:
    item = dict(row)
    if item.get('data_validade') is not None:
        item['data_validade'] = str(item['data_validade'])
    if item.get('data_entrada') is not None:
        item['data_entrada'] = str(item['data_entrada'])
    for campo in (
        'quantidade_atual', 'quantidade_inicial', 'estoque_min', 'estoque_total',
        'custo_unitario', 'preco_venda_unitario', 'valor_lote_custo', 'valor_lote_venda',
    ):
        if campo in item and item[campo] is not None:
            item[campo] = float(item[campo])
    item['vencido'] = _lote_vencido(item)
    item['status'] = _status_lote(item.get('dias_restantes'))
    return item



def registrar_movimento(
    *,
    produto_id: int,
    lote_id: int | None,
    tipo: str,
    quantidade: Decimal,
    anterior: Decimal | None,
    posterior: Decimal | None,
    motivo: str | None = None,
    valor_unitario: Decimal | None = None,
    observacao: str | None = None,
) -> None:
    vu = valor_unitario if value_is_positive(valor_unitario) else ZERO
    total = (quantidade or ZERO) * vu
    execute(
        """
        INSERT INTO movimentacoes_estoque (
            id_produto, id_lote, id_usuario, tipo_movimento,
            quantidade, quantidade_anterior, quantidade_posterior,
            motivo, valor_unitario, valor_total, observacao
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            produto_id,
            lote_id,
            getattr(current_user, 'id', None),
            tipo,
            quantidade,
            anterior,
            posterior,
            motivo,
            vu,
            total,
            observacao,
        ),
    )



def value_is_positive(value: Decimal | None) -> bool:
    return value is not None and value > 0



def _normalizar_motivo(dados, campo: str = 'motivo') -> str:
    return (dados.get(campo) or '').strip()



def _aplicar_saida_fifo(produto_id: int, quantidade: Decimal, motivo: str, observacao: str | None = None) -> tuple[list[dict], Decimal]:
    lotes_validos = query(
        """
        SELECT l.*, p.nome, p.unidade
          FROM lotes l
          JOIN produtos p ON p.id = l.id_produto
         WHERE l.id_produto = %s
           AND l.quantidade_atual > 0
           AND l.data_validade >= CURDATE()
         ORDER BY l.data_validade ASC, l.data_entrada ASC, l.id ASC
        """,
        (produto_id,),
    )
    lotes_vencidos = query(
        """
        SELECT COUNT(*) AS total, COALESCE(SUM(quantidade_atual), 0) AS saldo
          FROM lotes
         WHERE id_produto = %s
           AND quantidade_atual > 0
           AND data_validade < CURDATE()
        """,
        (produto_id,),
        fetchone=True,
    )
    total_disponivel = sum(Decimal(str(l['quantidade_atual'])) for l in lotes_validos)
    if total_disponivel < quantidade:
        extra = ''
        if Decimal(str(lotes_vencidos['saldo'] or 0)) > 0:
            extra = f' Existem {float(lotes_vencidos["saldo"]):.2f} unidades vencidas bloqueadas para saída normal.'
        raise ValueError(f'Estoque válido insuficiente. Disponível para saída: {total_disponivel}.{extra}')

    restante = quantidade
    consumos: list[dict] = []
    for lote in lotes_validos:
        if restante <= 0:
            break
        atual = Decimal(str(lote['quantidade_atual']))
        consumir = min(atual, restante)
        saldo = atual - consumir
        custo = Decimal(str(lote.get('custo_unitario') or 0))
        execute('UPDATE lotes SET quantidade_atual = %s WHERE id = %s', (saldo, lote['id']))
        registrar_movimento(
            produto_id=produto_id,
            lote_id=lote['id'],
            tipo='SAIDA',
            quantidade=consumir,
            anterior=atual,
            posterior=saldo,
            motivo=motivo,
            valor_unitario=custo,
            observacao=observacao,
        )
        consumos.append(
            {
                'lote_id': lote['id'],
                'codigo_lote': lote['codigo_lote'],
                'consumido': float(consumir),
                'saldo': float(saldo),
                'custo_total': float(consumir * custo),
            }
        )
        restante -= consumir
    return consumos, total_disponivel - quantidade


@inventory_bp.route('/inventario')
@login_required
def inventario():
    if current_user.is_liberacao():
        return render_template('dashboard/bloqueado.html')
    return render_template('inventory/inventario.html')


@inventory_bp.route('/saidas')
@login_required
def saidas_page():
    if current_user.is_liberacao():
        return render_template('dashboard/bloqueado.html')
    return render_template('inventory/saidas.html')


@inventory_bp.route('/cadastro')
@login_required
def cadastro():
    if not current_user.pode_cadastrar():
        registrar('ACESSO_NEGADO', 'Tentativa de acesso à página de cadastro sem permissão', 'Bloqueado')
        return render_template('dashboard/bloqueado.html')
    produtos = query(
        """
        SELECT p.id, p.nome, p.categoria, p.unidade, p.preco_referencia,
               COALESCE(SUM(l.quantidade_atual), 0) AS estoque_total,
               COALESCE(SUM(l.quantidade_atual * l.custo_unitario), 0) AS valor_estoque_custo
          FROM produtos p
          LEFT JOIN lotes l ON l.id_produto = p.id
         WHERE p.ativo = 1
         GROUP BY p.id, p.nome, p.categoria, p.unidade, p.preco_referencia
         ORDER BY p.nome
        """
    )
    return render_template('inventory/cadastro.html', produtos=produtos)


@inventory_bp.route('/movimentacoes')
@login_required
def movimentacoes_page():
    if current_user.is_liberacao():
        return render_template('dashboard/bloqueado.html')
    return render_template('inventory/movimentacoes.html')


@inventory_bp.route('/api/v1/estoque', methods=['GET'])
@login_required
def listar_estoque():
    rows = query(
        """
        SELECT l.id, l.id_produto, p.nome, p.categoria, p.unidade, p.estoque_min,
               p.preco_referencia,
               l.codigo_lote, l.quantidade_atual, l.quantidade_inicial,
               l.custo_unitario, l.preco_venda_unitario, l.fornecedor,
               (l.quantidade_atual * l.custo_unitario) AS valor_lote_custo,
               (l.quantidade_atual * l.preco_venda_unitario) AS valor_lote_venda,
               l.data_validade, l.data_entrada,
               DATEDIFF(l.data_validade, CURDATE()) AS dias_restantes,
               COALESCE(t.total_produto, 0) AS estoque_total
          FROM lotes l
          JOIN produtos p ON l.id_produto = p.id
          LEFT JOIN (
                SELECT id_produto, SUM(quantidade_atual) AS total_produto
                  FROM lotes
                 GROUP BY id_produto
          ) t ON t.id_produto = p.id
         WHERE p.ativo = 1
           AND l.quantidade_atual > 0
         ORDER BY l.data_validade ASC, p.nome ASC, l.codigo_lote ASC
        """
    )
    return jsonify([_serializar_lote(r) for r in rows])


@inventory_bp.route('/api/v1/produtos', methods=['GET'])
@login_required
def listar_produtos():
    rows = query(
        """
        SELECT p.id, p.nome, p.categoria, p.unidade, p.estoque_min, p.preco_referencia, p.ativo,
               COALESCE(SUM(l.quantidade_atual), 0) AS estoque_total,
               COALESCE(SUM(CASE WHEN l.data_validade >= CURDATE() THEN l.quantidade_atual ELSE 0 END), 0) AS estoque_valido,
               COALESCE(SUM(CASE WHEN l.data_validade < CURDATE() THEN l.quantidade_atual ELSE 0 END), 0) AS estoque_vencido,
               COALESCE(SUM(l.quantidade_atual * l.custo_unitario), 0) AS valor_estoque_custo,
               COALESCE(SUM(l.quantidade_atual * l.preco_venda_unitario), 0) AS valor_estoque_venda,
               COALESCE(SUM(CASE WHEN l.data_validade < CURDATE() THEN l.quantidade_atual * l.custo_unitario ELSE 0 END), 0) AS valor_vencido_custo,
               COUNT(l.id) AS total_lotes
          FROM produtos p
          LEFT JOIN lotes l ON l.id_produto = p.id
         WHERE p.ativo = 1
         GROUP BY p.id, p.nome, p.categoria, p.unidade, p.estoque_min, p.preco_referencia, p.ativo
         ORDER BY p.nome ASC
        """
    )
    produtos = []
    for row in rows:
        item = dict(row)
        for campo in ('estoque_total', 'estoque_min', 'estoque_valido', 'estoque_vencido', 'preco_referencia', 'valor_estoque_custo', 'valor_estoque_venda', 'valor_vencido_custo'):
            item[campo] = float(item[campo] or 0)
        produtos.append(item)
    return jsonify(produtos)


@inventory_bp.route('/api/v1/produto/<int:prod_id>/lotes-disponiveis', methods=['GET'])
@login_required
def lotes_disponiveis(prod_id: int):
    incluir_vencidos = (request.args.get('incluir_vencidos') or '').lower() in ('1', 'true', 'sim')
    rows = query(
        """
        SELECT l.id, l.id_produto, p.nome, p.unidade, p.categoria, p.estoque_min,
               p.preco_referencia, l.custo_unitario, l.preco_venda_unitario, l.fornecedor,
               l.codigo_lote, l.quantidade_atual, l.quantidade_inicial, l.data_validade, l.data_entrada,
               (l.quantidade_atual * l.custo_unitario) AS valor_lote_custo,
               (l.quantidade_atual * l.preco_venda_unitario) AS valor_lote_venda,
               DATEDIFF(l.data_validade, CURDATE()) AS dias_restantes
          FROM lotes l
          JOIN produtos p ON p.id = l.id_produto
         WHERE l.id_produto = %s
           AND l.quantidade_atual > 0
         ORDER BY l.data_validade ASC, l.data_entrada ASC, l.id ASC
        """,
        (prod_id,),
    )
    data = [_serializar_lote(r) for r in rows]
    if not incluir_vencidos:
        data = [r for r in data if not r['vencido']]
    return jsonify(data)


@inventory_bp.route('/api/v1/resumo-estoque', methods=['GET'])
@login_required
def resumo_estoque():
    totais = query(
        """
        SELECT COUNT(*) AS total_lotes,
               SUM(CASE WHEN quantidade_atual > 0 THEN 1 ELSE 0 END) AS lotes_ativos,
               SUM(CASE WHEN quantidade_atual > 0 AND data_validade < CURDATE() THEN 1 ELSE 0 END) AS vencidos,
               SUM(CASE WHEN quantidade_atual > 0 AND DATEDIFF(data_validade, CURDATE()) BETWEEN 0 AND 7 THEN 1 ELSE 0 END) AS criticos,
               SUM(CASE WHEN quantidade_atual > 0 AND DATEDIFF(data_validade, CURDATE()) BETWEEN 8 AND 15 THEN 1 ELSE 0 END) AS alertas,
               SUM(CASE WHEN quantidade_atual > 0 AND DATEDIFF(data_validade, CURDATE()) BETWEEN 16 AND 30 THEN 1 ELSE 0 END) AS avisos,
               COALESCE(SUM(quantidade_atual * custo_unitario), 0) AS valor_estoque_custo,
               COALESCE(SUM(CASE WHEN data_validade < CURDATE() THEN quantidade_atual * custo_unitario ELSE 0 END), 0) AS valor_vencido_custo
          FROM lotes
        """,
        fetchone=True,
    )
    estoque_baixo = query(
        """
        SELECT COUNT(*) AS total
          FROM (
                SELECT p.id
                  FROM produtos p
                  LEFT JOIN lotes l ON l.id_produto = p.id
                 WHERE p.ativo = 1
                 GROUP BY p.id, p.estoque_min
                HAVING COALESCE(SUM(l.quantidade_atual), 0) <= p.estoque_min
          ) x
        """,
        fetchone=True,
    )
    perdas = query(
        """
        SELECT COALESCE(SUM(valor_total), 0) AS perdas_total
          FROM movimentacoes_estoque
         WHERE tipo_movimento IN ('DESCARTE_VENCIDO', 'AVARIA')
        """,
        fetchone=True,
    )
    recentes = query(
        """
        SELECT m.id, m.tipo_movimento, m.quantidade, m.valor_total, m.motivo, m.criado_em,
               p.nome AS produto_nome, l.codigo_lote, u.login AS usuario
          FROM movimentacoes_estoque m
          JOIN produtos p ON p.id = m.id_produto
          LEFT JOIN lotes l ON l.id = m.id_lote
          LEFT JOIN usuarios u ON u.id = m.id_usuario
         ORDER BY m.criado_em DESC, m.id DESC
         LIMIT 8
        """
    )
    return jsonify(
        {
            'totais': {
                'total_lotes': int(totais['total_lotes'] or 0),
                'lotes_ativos': int(totais['lotes_ativos'] or 0),
                'vencidos': int(totais['vencidos'] or 0),
                'criticos': int(totais['criticos'] or 0),
                'alertas': int(totais['alertas'] or 0),
                'avisos': int(totais['avisos'] or 0),
                'estoque_baixo': int(estoque_baixo['total'] or 0),
                'valor_estoque_custo': float(totais['valor_estoque_custo'] or 0),
                'valor_vencido_custo': float(totais['valor_vencido_custo'] or 0),
                'perdas_total': float(perdas['perdas_total'] or 0),
            },
            'movimentacoes_recentes': [
                {
                    'id': r['id'],
                    'tipo_movimento': r['tipo_movimento'],
                    'quantidade': float(r['quantidade'] or 0),
                    'valor_total': float(r['valor_total'] or 0),
                    'motivo': r['motivo'],
                    'criado_em': str(r['criado_em']),
                    'produto_nome': r['produto_nome'],
                    'codigo_lote': r['codigo_lote'],
                    'usuario': r['usuario'],
                }
                for r in recentes
            ],
        }
    )


@inventory_bp.route('/api/v1/movimentacoes', methods=['GET'])
@login_required
def listar_movimentacoes():
    tipo = (request.args.get('tipo') or '').strip().upper()
    termo = (request.args.get('q') or '').strip()
    sql = """
        SELECT m.id, m.tipo_movimento, m.quantidade, m.quantidade_anterior,
               m.quantidade_posterior, m.motivo, m.valor_unitario, m.valor_total,
               m.observacao, m.criado_em,
               p.nome AS produto_nome, p.unidade,
               l.codigo_lote, u.login AS usuario
          FROM movimentacoes_estoque m
          JOIN produtos p ON p.id = m.id_produto
          LEFT JOIN lotes l ON l.id = m.id_lote
          LEFT JOIN usuarios u ON u.id = m.id_usuario
         WHERE 1=1
    """
    params: list[object] = []
    if tipo:
        sql += ' AND m.tipo_movimento = %s'
        params.append(tipo)
    if termo:
        sql += ' AND (p.nome LIKE %s OR COALESCE(l.codigo_lote, "") LIKE %s OR COALESCE(m.observacao, "") LIKE %s OR COALESCE(m.motivo, "") LIKE %s)'
        like = f'%{termo}%'
        params.extend([like, like, like, like])
    sql += ' ORDER BY m.criado_em DESC, m.id DESC LIMIT 300'
    rows = query(sql, tuple(params))
    return jsonify(
        [
            {
                'id': r['id'],
                'tipo_movimento': r['tipo_movimento'],
                'quantidade': float(r['quantidade'] or 0),
                'quantidade_anterior': float(r['quantidade_anterior'] or 0) if r['quantidade_anterior'] is not None else None,
                'quantidade_posterior': float(r['quantidade_posterior'] or 0) if r['quantidade_posterior'] is not None else None,
                'motivo': r['motivo'],
                'valor_unitario': float(r['valor_unitario'] or 0),
                'valor_total': float(r['valor_total'] or 0),
                'observacao': r['observacao'],
                'criado_em': str(r['criado_em']),
                'produto_nome': r['produto_nome'],
                'unidade': r['unidade'],
                'codigo_lote': r['codigo_lote'],
                'usuario': r['usuario'],
            }
            for r in rows
        ]
    )


@inventory_bp.route('/api/v1/novo_produto', methods=['POST'])
@login_required
def novo_produto():
    if not current_user.pode_cadastrar():
        registrar('CADASTRO_PRODUTO', 'Tentativa sem permissão', 'Bloqueado')
        return jsonify({'erro': 'Sem permissão'}), 403

    dados = request.get_json() or request.form
    nome = (dados.get('nome') or '').strip()
    if not nome:
        return jsonify({'erro': 'Nome obrigatório'}), 400

    categoria = (dados.get('categoria') or 'Geral').strip() or 'Geral'
    unidade = (dados.get('unidade') or 'UN').strip() or 'UN'
    minimo = _to_decimal(dados.get('minimo'), '1')
    preco_ref = _to_decimal(dados.get('preco_referencia'), '0')
    if minimo < 0 or preco_ref < 0:
        return jsonify({'erro': 'Valores inválidos'}), 400

    existe = query('SELECT id FROM produtos WHERE nome = %s', (nome,), fetchone=True)
    if existe:
        return jsonify({'erro': 'Produto já cadastrado'}), 409

    pid = execute(
        'INSERT INTO produtos (nome, categoria, unidade, estoque_min, preco_referencia) VALUES (%s, %s, %s, %s, %s)',
        (nome, categoria, unidade, minimo, preco_ref),
    )
    registrar('CADASTRO_PRODUTO', f'Produto cadastrado: {nome} (id={pid})', dados_depois={'id': pid, 'nome': nome, 'preco_referencia': float(preco_ref)})
    return jsonify({'sucesso': True, 'id': pid}), 201


@inventory_bp.route('/api/v1/novo_lote', methods=['POST'])
@login_required
def novo_lote():
    if not current_user.pode_cadastrar():
        registrar('CADASTRO_LOTE', 'Tentativa sem permissão', 'Bloqueado')
        return jsonify({'erro': 'Sem permissão'}), 403

    dados = request.get_json() or request.form
    id_prod = dados.get('id_produto')
    codigo = (dados.get('codigo') or '').strip()
    qtd = _to_decimal(dados.get('quantidade'))
    validade = dados.get('validade')
    custo_unitario = _to_decimal(dados.get('custo_unitario'), '0')
    preco_venda = _to_decimal(dados.get('preco_venda_unitario'), '0')
    fornecedor = (dados.get('fornecedor') or '').strip() or None

    if not id_prod or not codigo or qtd <= 0 or not validade:
        return jsonify({'erro': 'Campos obrigatórios faltando ou inválidos'}), 400
    validade_dt = _parse_date(validade)
    if not validade_dt:
        return jsonify({'erro': 'Data de validade inválida'}), 400
    if validade_dt < date.today():
        return jsonify({'erro': 'Não é permitido cadastrar entrada inicial com lote já vencido'}), 400
    if custo_unitario < 0 or preco_venda < 0:
        return jsonify({'erro': 'Custos e preços devem ser positivos'}), 400
    if value_is_positive(preco_venda) and preco_venda < custo_unitario:
        return jsonify({'erro': 'Preço de venda não pode ser menor que o custo unitário'}), 400

    produto = query('SELECT id, nome FROM produtos WHERE id=%s AND ativo=1', (id_prod,), fetchone=True)
    if not produto:
        return jsonify({'erro': 'Produto não encontrado'}), 404

    lid = execute(
        """
        INSERT INTO lotes (
            id_produto, codigo_lote, quantidade_atual, quantidade_inicial,
            custo_unitario, preco_venda_unitario, fornecedor,
            data_validade, id_usuario_entry
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (id_prod, codigo, qtd, qtd, custo_unitario, preco_venda, fornecedor, validade, current_user.id),
    )
    registrar_movimento(
        produto_id=int(id_prod),
        lote_id=lid,
        tipo='ENTRADA',
        quantidade=qtd,
        anterior=ZERO,
        posterior=qtd,
        motivo='Entrada de estoque',
        valor_unitario=custo_unitario,
        observacao='Entrada inicial de lote',
    )
    registrar(
        'CADASTRO_LOTE',
        f'Lote {codigo} cadastrado — {produto["nome"]} x{qtd} val:{validade}',
        dados_depois={
            'lote_id': lid,
            'codigo': codigo,
            'qtd': float(qtd),
            'validade': validade,
            'custo_unitario': float(custo_unitario),
            'preco_venda_unitario': float(preco_venda),
        },
    )
    return jsonify({'sucesso': True, 'id': lid}), 201


@inventory_bp.route('/api/v1/lote/<int:lote_id>/baixa', methods=['POST'])
@login_required
def dar_baixa(lote_id: int):
    if not current_user.pode_editar():
        registrar('BAIXA_ESTOQUE', f'Tentativa de baixa no lote {lote_id} sem permissão', 'Bloqueado')
        return jsonify({'erro': 'Sem permissão'}), 403

    dados = request.get_json() or {}
    qtd = _to_decimal(dados.get('quantidade'), '1')
    motivo = _normalizar_motivo(dados)
    observacao = (dados.get('observacao') or 'Saída manual por lote').strip() or 'Saída manual por lote'
    if qtd <= 0:
        return jsonify({'erro': 'Quantidade inválida'}), 400
    if not motivo:
        return jsonify({'erro': 'Informe o motivo da saída'}), 400

    lote = query(
        """
        SELECT l.*, p.nome
          FROM lotes l
          JOIN produtos p ON p.id = l.id_produto
         WHERE l.id=%s
        """,
        (lote_id,),
        fetchone=True,
    )
    if not lote:
        return jsonify({'erro': 'Lote não encontrado'}), 404

    if _lote_vencido(lote):
        registrar(
            'BAIXA_BLOQUEADA_VENCIDO',
            f'Tentativa de saída normal do lote vencido {lote["codigo_lote"]}',
            'Bloqueado',
            dados_antes={'lote_id': lote_id, 'quantidade_atual': float(lote['quantidade_atual'])},
        )
        return jsonify({'erro': 'Lote vencido. Use a operação de descarte para produtos vencidos.'}), 400

    atual = Decimal(str(lote['quantidade_atual']))
    if atual < qtd:
        return jsonify({'erro': 'Quantidade insuficiente no lote'}), 400

    nova_qtd = atual - qtd
    custo = Decimal(str(lote.get('custo_unitario') or 0))
    execute('UPDATE lotes SET quantidade_atual=%s WHERE id=%s', (nova_qtd, lote_id))
    registrar_movimento(
        produto_id=lote['id_produto'],
        lote_id=lote_id,
        tipo='SAIDA',
        quantidade=qtd,
        anterior=atual,
        posterior=nova_qtd,
        motivo=motivo,
        valor_unitario=custo,
        observacao=observacao,
    )
    registrar(
        'BAIXA_ESTOQUE',
        f'Baixa de {qtd} un. no lote {lote["codigo_lote"]} — saldo: {nova_qtd}',
        dados_antes={'quantidade': float(atual)},
        dados_depois={'quantidade': float(nova_qtd), 'motivo': motivo},
    )
    return jsonify({'sucesso': True, 'saldo': float(nova_qtd)})


@inventory_bp.route('/api/v1/produto/<int:prod_id>/saida_fifo', methods=['POST'])
@login_required
def saida_fifo(prod_id: int):
    if not current_user.pode_editar():
        registrar('SAIDA_FIFO', f'Tentativa sem permissão no produto {prod_id}', 'Bloqueado')
        return jsonify({'erro': 'Sem permissão'}), 403

    dados = request.get_json() or {}
    qtd = _to_decimal(dados.get('quantidade'))
    motivo = _normalizar_motivo(dados)
    observacao = (dados.get('observacao') or 'Saída automática FIFO').strip() or 'Saída automática FIFO'
    if qtd <= 0:
        return jsonify({'erro': 'Quantidade inválida'}), 400
    if not motivo:
        return jsonify({'erro': 'Informe o motivo da saída'}), 400

    produto = query('SELECT id, nome, unidade FROM produtos WHERE id=%s AND ativo=1', (prod_id,), fetchone=True)
    if not produto:
        return jsonify({'erro': 'Produto não encontrado'}), 404

    try:
        consumos, saldo_total = _aplicar_saida_fifo(prod_id, qtd, motivo, observacao)
    except ValueError as exc:
        registrar(
            'SAIDA_FIFO_BLOQUEADA',
            f'Tentativa de saída FIFO bloqueada no produto {prod_id}: {exc}',
            'Bloqueado',
            dados_depois={'produto_id': prod_id, 'quantidade': float(qtd)},
        )
        return jsonify({'erro': str(exc)}), 400

    registrar(
        'SAIDA_FIFO',
        f'Saída FIFO de {qtd} {produto["unidade"]} do produto {produto["nome"]}',
        dados_depois={'produto_id': prod_id, 'consumos': consumos, 'saldo_total': float(saldo_total), 'motivo': motivo},
    )
    return jsonify({'sucesso': True, 'consumos': consumos, 'saldo_total': float(saldo_total)})


@inventory_bp.route('/api/v1/lote/<int:lote_id>/descartar', methods=['POST'])
@login_required
def descartar_vencido(lote_id: int):
    if not current_user.pode_editar():
        registrar('DESCARTE_VENCIDO', f'Tentativa sem permissão no lote {lote_id}', 'Bloqueado')
        return jsonify({'erro': 'Sem permissão'}), 403

    dados = request.get_json() or {}
    qtd = _to_decimal(dados.get('quantidade'), '0')
    motivo = _normalizar_motivo(dados)
    observacao = (dados.get('observacao') or '').strip()
    if qtd <= 0:
        return jsonify({'erro': 'Quantidade inválida'}), 400
    if not motivo:
        return jsonify({'erro': 'Informe o motivo do descarte'}), 400

    lote = query(
        """
        SELECT l.*, p.nome
          FROM lotes l
          JOIN produtos p ON p.id = l.id_produto
         WHERE l.id=%s
        """,
        (lote_id,),
        fetchone=True,
    )
    if not lote:
        return jsonify({'erro': 'Lote não encontrado'}), 404
    if not _lote_vencido(lote):
        return jsonify({'erro': 'Descarte por vencimento só é permitido para lotes vencidos'}), 400

    atual = Decimal(str(lote['quantidade_atual']))
    if atual < qtd:
        return jsonify({'erro': 'Quantidade insuficiente no lote'}), 400

    nova_qtd = atual - qtd
    custo = Decimal(str(lote.get('custo_unitario') or 0))
    obs = f'Descarte de vencido — motivo: {motivo}'
    if observacao:
        obs += f' | {observacao}'

    execute('UPDATE lotes SET quantidade_atual=%s WHERE id=%s', (nova_qtd, lote_id))
    registrar_movimento(
        produto_id=lote['id_produto'],
        lote_id=lote_id,
        tipo='DESCARTE_VENCIDO',
        quantidade=qtd,
        anterior=atual,
        posterior=nova_qtd,
        motivo=motivo,
        valor_unitario=custo,
        observacao=obs,
    )
    registrar(
        'DESCARTE_VENCIDO',
        f'Descarte de {qtd} no lote vencido {lote["codigo_lote"]}',
        dados_antes={'quantidade': float(atual)},
        dados_depois={'quantidade': float(nova_qtd), 'motivo': motivo, 'perda_custo': float(qtd * custo)},
    )
    return jsonify({'sucesso': True, 'saldo': float(nova_qtd), 'perda': float(qtd * custo)})


@inventory_bp.route('/api/v1/lote/<int:lote_id>/ajuste', methods=['POST'])
@login_required
def ajustar_lote(lote_id: int):
    if not current_user.pode_editar():
        registrar('AJUSTE_ESTOQUE', f'Tentativa sem permissão no lote {lote_id}', 'Bloqueado')
        return jsonify({'erro': 'Sem permissão'}), 403

    dados = request.get_json() or {}
    nova_quantidade = _to_decimal(dados.get('nova_quantidade'))
    motivo = _normalizar_motivo(dados)
    observacao = (dados.get('observacao') or 'Ajuste manual de estoque').strip() or 'Ajuste manual de estoque'
    if nova_quantidade < 0:
        return jsonify({'erro': 'Nova quantidade inválida'}), 400

    lote = query('SELECT * FROM lotes WHERE id=%s', (lote_id,), fetchone=True)
    if not lote:
        return jsonify({'erro': 'Lote não encontrado'}), 404

    anterior = Decimal(str(lote['quantidade_atual']))
    if nova_quantidade != anterior and not motivo:
        return jsonify({'erro': 'Informe o motivo do ajuste'}), 400

    execute('UPDATE lotes SET quantidade_atual=%s WHERE id=%s', (nova_quantidade, lote_id))
    tipo = 'AJUSTE_POSITIVO' if nova_quantidade >= anterior else 'AJUSTE_NEGATIVO'
    custo = Decimal(str(lote.get('custo_unitario') or 0))
    registrar_movimento(
        produto_id=lote['id_produto'],
        lote_id=lote_id,
        tipo=tipo,
        quantidade=abs(nova_quantidade - anterior),
        anterior=anterior,
        posterior=nova_quantidade,
        motivo=motivo,
        valor_unitario=custo,
        observacao=observacao,
    )
    registrar(
        'AJUSTE_ESTOQUE',
        f'Ajuste manual no lote {lote["codigo_lote"]}: {anterior} -> {nova_quantidade}',
        dados_antes={'quantidade': float(anterior)},
        dados_depois={'quantidade': float(nova_quantidade), 'observacao': observacao, 'motivo': motivo},
    )
    return jsonify({'sucesso': True, 'saldo': float(nova_quantidade)})


@inventory_bp.route('/api/v1/lote/<int:lote_id>/avaria', methods=['POST'])
@login_required
def registrar_avaria(lote_id: int):
    if not current_user.pode_editar():
        registrar('AVARIA_ESTOQUE', f'Tentativa sem permissão no lote {lote_id}', 'Bloqueado')
        return jsonify({'erro': 'Sem permissão'}), 403

    dados = request.get_json() or {}
    qtd = _to_decimal(dados.get('quantidade'), '0')
    motivo = _normalizar_motivo(dados)
    observacao = (dados.get('observacao') or '').strip()
    if qtd <= 0:
        return jsonify({'erro': 'Quantidade inválida'}), 400
    if not motivo:
        return jsonify({'erro': 'Informe o motivo da avaria'}), 400

    lote = query('SELECT * FROM lotes WHERE id=%s', (lote_id,), fetchone=True)
    if not lote:
        return jsonify({'erro': 'Lote não encontrado'}), 404

    atual = Decimal(str(lote['quantidade_atual']))
    if atual < qtd:
        return jsonify({'erro': 'Quantidade insuficiente no lote'}), 400

    nova_qtd = atual - qtd
    custo = Decimal(str(lote.get('custo_unitario') or 0))
    execute('UPDATE lotes SET quantidade_atual=%s WHERE id=%s', (nova_qtd, lote_id))
    registrar_movimento(
        produto_id=lote['id_produto'],
        lote_id=lote_id,
        tipo='AVARIA',
        quantidade=qtd,
        anterior=atual,
        posterior=nova_qtd,
        motivo=motivo,
        valor_unitario=custo,
        observacao=observacao or 'Baixa por avaria',
    )
    return jsonify({'sucesso': True, 'saldo': float(nova_qtd), 'perda': float(qtd * custo)})


@inventory_bp.route('/api/v1/lote/<int:lote_id>', methods=['DELETE'])
@login_required
def excluir_lote(lote_id: int):
    if not current_user.pode_excluir():
        registrar('EXCLUSAO_LOTE', f'Tentativa de exclusão do lote {lote_id} sem permissão', 'Bloqueado')
        return jsonify({'erro': 'Sem permissão'}), 403

    lote = query('SELECT * FROM lotes WHERE id=%s', (lote_id,), fetchone=True)
    if not lote:
        return jsonify({'erro': 'Lote não encontrado'}), 404

    atual = Decimal(str(lote['quantidade_atual']))
    custo = Decimal(str(lote.get('custo_unitario') or 0))
    if atual > 0:
        registrar_movimento(
            produto_id=lote['id_produto'],
            lote_id=lote_id,
            tipo='EXCLUSAO',
            quantidade=atual,
            anterior=atual,
            posterior=ZERO,
            motivo='Exclusão de lote',
            valor_unitario=custo,
            observacao='Exclusão de lote com encerramento de saldo',
        )
    execute('DELETE FROM lotes WHERE id=%s', (lote_id,))
    registrar(
        'EXCLUSAO_LOTE',
        f'Lote {lote["codigo_lote"]} excluído',
        dados_antes={'codigo': lote['codigo_lote'], 'qtd': float(atual)},
    )
    return jsonify({'sucesso': True})
