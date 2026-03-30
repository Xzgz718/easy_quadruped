from __future__ import annotations

from pathlib import Path

from export_markdown_pdf import export_markdown_pdf
from generate_tutorial_diagrams import main as generate_diagrams


def main() -> None:
    docs_dir = Path(__file__).resolve().parent
    tutorial_dir = docs_dir / "mujoco_quadruped_mastery_tutorial"
    markdown_path = tutorial_dir / "mujoco_quadruped_mastery_tutorial.md"
    pdf_path = tutorial_dir / "mujoco_quadruped_mastery_tutorial.pdf"

    generate_diagrams()
    export_markdown_pdf(markdown_path, pdf_path)
    print(pdf_path)


if __name__ == "__main__":
    main()
