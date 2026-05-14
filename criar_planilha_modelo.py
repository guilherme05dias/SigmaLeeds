"""
criar_planilha_modelo.py — Execute este script para gerar a planilha modelo.
Uso: python criar_planilha_modelo.py
"""
from database.services.template_xlsx import build_template_workbook


def main() -> None:
    """Gera contatos_modelo.xlsx na raiz do projeto."""
    output = "contatos_modelo.xlsx"
    workbook = build_template_workbook()
    workbook.save(output)
    print(f"Planilha criada: {output}")
    print("Edite os dados de exemplo com seus contatos reais e defina Status=PENDENTE.")


if __name__ == "__main__":
    main()
