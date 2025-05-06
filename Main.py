import tkinter as tk
from tkinter import ttk
import re
import networkx as nx
import matplotlib.pyplot as plt
from networkx.drawing.nx_agraph import graphviz_layout

METADADOS = {
    "Categoria": ["idCategoria", "Descricao"],
    "Produto": ["idProduto", "Nome", "Descricao", "Preco", "QuantEstoque", "Categoria_idCategoria"],
    "TipoCliente": ["idTipoCliente", "Descricao"],
    "Cliente": ["idCliente", "Nome", "Email", "Nascimento", "Senha", "TipoCliente_idTipoCliente", "DataRegistro"],
    "TipoEndereco": ["idTipoEndereco", "Descricao"],
    "Endereco": [
        "idEndereco", "EnderecoPadrao", "Logradouro", "Numero", "Complemento", "Bairro", "Cidade",
        "UF", "CEP", "TipoEndereco_idTipoEndereco", "Cliente_idCliente"
    ],
    "Telefone": ["Numero", "Cliente_idCliente"],
    "Status": ["idStatus", "Descricao"],
    "Pedido": ["idPedido", "Status_idStatus", "DataPedido", "ValorTotalPedido", "Cliente_idCliente"],
    "Pedido_has_Produto": ["idPedidoProduto", "Pedido_idPedido", "Produto_idProduto", "Quantidade", "PrecoUnitario"]
}

def validar_esquema(partes):
    metadados_lower = {tabela.lower(): [col.lower() for col in colunas] for tabela, colunas in METADADOS.items()}

    tabela_from = partes["FROM"].lower()
    if tabela_from not in metadados_lower:
        raise ValueError(f"Tabela '{partes['FROM']}' não encontrada no esquema.")

    colunas_select = [col.strip() for col in partes["SELECT"].split(",")]
    for coluna in colunas_select:
        if coluna == "*":
            continue
        if "." in coluna:
            tabela, col = [x.strip() for x in coluna.split(".", 1)]
            if tabela.lower() not in metadados_lower:
                raise ValueError(f"Tabela '{tabela}' não encontrada no esquema (ao referenciar '{coluna}').")
            if col.lower() not in metadados_lower[tabela.lower()]:
                raise ValueError(f"Coluna '{col}' não encontrada na tabela '{tabela}'.")
        else:
            if coluna.lower() not in metadados_lower[tabela_from]:
                raise ValueError(f"Coluna '{coluna}' não encontrada na tabela '{partes['FROM']}'.")

    for join in partes["JOIN"]:
        tabela_join = join['tabela'].lower()
        if tabela_join not in metadados_lower:
            raise ValueError(f"Tabela de JOIN '{join['tabela']}' não encontrada no esquema.")


class OperatorNode:
    def __init__(self, op_type, children=None, predicate=None, table_name=None, projection_list=None):
        self.op_type = op_type             
        self.children = children if children is not None else []
        self.predicate = predicate          
        self.table_name = table_name       
        self.projection_list = projection_list 

    def __str__(self):
        if self.op_type == "TABLE":
            return f"TABELA({self.table_name})"
        elif self.op_type == "SELECTION":
            return f"SELEÇÃO({self.predicate})"
        elif self.op_type == "JOIN":
            return f"JUNÇÃO({self.predicate})"
        elif self.op_type == "PROJECTION":
            return f"PROJEÇÃO({self.projection_list})"
        else:
            return self.op_type

def build_operator_graph(partes):
    tree = OperatorNode("TABLE", table_name=partes["FROM"])

    for join in partes["JOIN"]:
        right_table = OperatorNode("TABLE", table_name=join["tabela"])
        tree = OperatorNode("JOIN", children=[tree, right_table], predicate=join["condicao"])

    if partes["WHERE"]:
        tree = OperatorNode("SELECTION", children=[tree], predicate=partes["WHERE"])

    if partes["SELECT"].strip() != "*":
        proj_list = [col.strip() for col in partes["SELECT"].split(",")]
        tree = OperatorNode("PROJECTION", children=[tree], projection_list=proj_list)

    return tree

def build_nx_graph_from_operator(node, G, parent_id=None, counter=[0]):
    current_id = counter[0]
    counter[0] += 1
    G.add_node(current_id, label=str(node))
    if parent_id is not None:
        G.add_edge(parent_id, current_id)
    for child in node.children:
        build_nx_graph_from_operator(child, G, current_id, counter)
    return G

def draw_operator_graph_visual(operator_node):
    G = nx.DiGraph()
    G = build_nx_graph_from_operator(operator_node, G)
    try:
        pos = graphviz_layout(G, prog='dot')
    except:
        pos = nx.spring_layout(G)
    labels = nx.get_node_attributes(G, 'label')
    plt.figure(figsize=(8, 6))
    nx.draw(G, pos, with_labels=True, labels=labels, node_color='lightblue', 
            node_size=2000, arrows=True, arrowstyle='->', font_size=9)
    plt.title("Grafo de Operadores")
    plt.axis('off')
    plt.show()

def display_operator_graph(node, indent=0):
    representation = "  " * indent + str(node) + "\n"
    for child in node.children:
        representation += display_operator_graph(child, indent + 1)
    return representation

def get_execution_order(node):
    steps = []
    for child in node.children:
        steps.extend(get_execution_order(child))
    steps.append(str(node))
    return steps

class SQLProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Processador de Consultas SQL")

        ttk.Label(root, text="Consulta SQL:").pack()
        self.sql_entry = tk.Text(root, height=5)
        self.sql_entry.pack(fill=tk.X, padx=10)

        ttk.Button(root, text="Executar", command=self.executar_consulta).pack(pady=10)

        self.relacional_text = self.create_output("Álgebra Relacional")
        self.ordem_text = self.create_output("Ordem de Execução Otimizada")
        self.grafo_text = self.create_output("Grafo de Operadores (Texto)")

    def create_output(self, title):
        frame = ttk.LabelFrame(self.root, text=title)
        frame.pack(fill=tk.X, padx=10, pady=5)
        text = tk.Text(frame, height=8, fg='black')
        text.pack(fill=tk.X)
        return text

    def parse_sql(self, sql):
        partes = {"SELECT": "", "FROM": "", "JOIN": [], "WHERE": ""}
        sql = re.sub(r"\s+", " ", sql.strip())

        select_match = re.search(r"SELECT (.+?) FROM", sql, re.IGNORECASE)
        from_match = re.search(r"FROM (\w+)", sql, re.IGNORECASE)
        if not select_match or not from_match:
            raise ValueError("Consulta SQL inválida: certifique-se de que a consulta contenha as cláusulas SELECT e FROM.")

        joins = re.findall(r"JOIN\s+(\w+)\s+ON\s+(.+?)(?=\s+JOIN|\s+WHERE|$)", sql, re.IGNORECASE)
        where_match = re.search(r"WHERE (.+)", sql, re.IGNORECASE)

        partes["SELECT"] = select_match.group(1).strip()
        partes["FROM"] = from_match.group(1).strip()
        if joins:
            partes["JOIN"] = [{"tabela": j[0], "condicao": j[1].strip()} for j in joins]
        if where_match:
            partes["WHERE"] = where_match.group(1).strip()

        return partes

    def executar_consulta(self):
        sql = self.sql_entry.get("1.0", tk.END).strip()
        if sql.endswith(';'):
            sql = sql[:-1].strip()
        if not sql:
            self.relacional_text.delete("1.0", tk.END)
            self.relacional_text.insert(tk.END, "A consulta SQL está vazia. Por favor, insira uma consulta válida.")
            return

        try:
            partes = self.parse_sql(sql)
            validar_esquema(partes)
        except Exception as e:
            self.relacional_text.delete("1.0", tk.END)
            self.relacional_text.insert(tk.END, f"Erro: {str(e)}")
            return

        if partes["JOIN"]:
            join_chain = partes["FROM"] + " ⨝ " + " ⨝ ".join(
                [f"{j['tabela']} ON {j['condicao']}" for j in partes["JOIN"]]
            )
        else:
            join_chain = partes["FROM"]

        if partes["WHERE"]:
            relacao = f"σ({partes['WHERE']})({join_chain})"
        else:
            relacao = join_chain

        projecao = f"π({partes['SELECT']})({relacao})"

        self.relacional_text.delete("1.0", tk.END)
        self.relacional_text.insert(tk.END, projecao)

        operador_raiz = build_operator_graph(partes)

        grafo_str = display_operator_graph(operador_raiz)
        self.grafo_text.delete("1.0", tk.END)
        self.grafo_text.insert(tk.END, grafo_str)

        ordem_exec = get_execution_order(operador_raiz)
        ordem_exec_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(ordem_exec))
        self.ordem_text.delete("1.0", tk.END)
        self.ordem_text.insert(tk.END, ordem_exec_str)

        draw_operator_graph_visual(operador_raiz)

if __name__ == "__main__":
    root = tk.Tk()
    app = SQLProcessorGUI(root)
    root.mainloop()
