"""
Script to migrate data from JSON files to the SQL database.
"""

import json
import sys
from datetime import date
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, text

# Add the backend directory to sys.path
current_dir = Path(__file__).parent.absolute()
backend_dir = current_dir.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from app.adapters.sql_models import (  # noqa: E402
    ExperienceModel,
    FormationModel,
    ProjectModel,
    AboutModel,
    StackModel,
)
from app.settings import settings  # noqa: E402

# Use synchronous engine
DATABASE_URL_SYNC = settings.database_url.replace("+aiosqlite", "")
engine = create_engine(DATABASE_URL_SYNC)

DADOS_PATH = backend_dir / "dados"


def carregar_json(nome: str):
    caminho = DADOS_PATH / nome
    if not caminho.exists():
        print(f"Warning: File {nome} not found in {DADOS_PATH}")
        return None
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def migrar():
    """Executes data migration with manual JSON serialization on all complex fields."""
    print(f"--- Starting Migration to {DATABASE_URL_SYNC} ---")

    # Create tables if they don't exist
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # Limpar dados existentes
        session.execute(text("DELETE FROM about"))
        session.execute(text("DELETE FROM projects"))
        session.execute(text("DELETE FROM experiences"))
        session.execute(text("DELETE FROM formacoes"))
        session.execute(text("DELETE FROM stack"))

        # 1. About Section
        about_dados = carregar_json("about.json")
        if about_dados:
            # Manual serialization
            if isinstance(about_dados.get("descricao"), (dict, list)):
                about_dados["descricao"] = json.dumps(
                    about_dados["descricao"], ensure_ascii=False
                )
            if isinstance(about_dados.get("disponibilidade"), (dict, list)):
                about_dados["disponibilidade"] = json.dumps(
                    about_dados["disponibilidade"], ensure_ascii=False
                )

            about = AboutModel(**about_dados)
            session.add(about)
            print("✓ 'About' section data migrated.")

        # 2. Projects
        projects_dados = carregar_json("projects.json")
        if projects_dados:
            for p in projects_dados:
                for field in [
                    "descricao_curta",
                    "descricao_completa",
                    "tecnologias",
                    "funcionalidades",
                    "aprendizados",
                ]:
                    if field in p and isinstance(p[field], (dict, list)):
                        p[field] = json.dumps(p[field], ensure_ascii=False)
                project = ProjectModel(**p)
                session.add(project)
            print(f"✓ {len(projects_dados)} projects migrated.")

        # 3. Experiências Profissionais
        exp_dados = carregar_json("experiences.json")
        if exp_dados:
            for e in exp_dados:
                # Datas
                e["data_inicio"] = date.fromisoformat(e["data_inicio"])
                if e.get("data_fim"):
                    e["data_fim"] = date.fromisoformat(e["data_fim"])

                # Manual serialization of complex fields
                for field in ["cargo", "descricao", "tecnologias"]:
                    if field in e and isinstance(e[field], (dict, list)):
                        e[field] = json.dumps(e[field], ensure_ascii=False)

                exp = ExperienceModel(**e)
                session.add(exp)
            print(f"✓ {len(exp_dados)} experiences migrated.")

        # 4. Academic Formation
        form_dados = carregar_json("formation.json")
        if form_dados:
            for f in form_dados:
                f["data_inicio"] = date.fromisoformat(f["data_inicio"])
                if f.get("data_fim"):
                    f["data_fim"] = date.fromisoformat(f["data_fim"])

                # Manual serialization of complex fields
                for field in ["curso", "descricao"]:
                    if field in f and isinstance(f[field], (dict, list)):
                        f[field] = json.dumps(f[field], ensure_ascii=False)

                form = FormationModel(**f)
                session.add(form)
            print(f"✓ {len(form_dados)} formation items migrated.")

        # 5. Technological Stack
        stack_dados = carregar_json("stack.json")
        if stack_dados:
            for s in stack_dados:
                stack = StackModel(**s)
                session.add(stack)
            print(f"✓ {len(stack_dados)} stack technologies migrated.")

        session.commit()

    print("\n--- Migration completed successfully! ---")


if __name__ == "__main__":
    try:
        migrar()
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
