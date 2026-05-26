"""
Main entry point for SAS to PySpark translator.

Orchestrates parsing, semantic analysis, IR generation, and code emission.
"""

from pathlib import Path
from typing import Optional

from translator.emitters import PySparkEmitter
from translator.ir import IRProgram
from translator.parser import ASTBuilder, SASParser
from translator.semantic.lower import SASLowerer


class SASTranslator:
    """Main translator class orchestrating the translation pipeline."""

    def __init__(self):
        self.parser = SASParser()
        self.emitter = PySparkEmitter()

    def translate_file(self, input_path: Path) -> str:
        """Translate a single SAS file to PySpark code."""
        with open(input_path, "r") as f:
            sas_code = f.read()

        return self.translate_source(sas_code)

    def translate_source(self, source_code: str) -> str:
        """Translate SAS source code to PySpark.

        Pipeline:
        1. Parse SAS code to AST
        2. Lower AST to IR (semantic lowering)
        3. Emit PySpark code from IR
        """
        # Step 1: Parse SAS code
        ast_dict = self.parser.parse(source_code)
        if not ast_dict:
            return "# Failed to parse SAS code"

        # Step 2: Build typed AST
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        # Step 3: Semantic lowering (AST → IR)
        # Now handles multiple DATA steps and multiple datasets properly
        ir_program = self._lower_to_ir(ast_root)

        # Step 4: Generate PySpark code
        pyspark_code = self.emitter.emit_program(ir_program)

        return pyspark_code

    def _lower_to_ir(self, ast_root) -> IRProgram:
        """Lower AST to IR using semantic lowering.

        This step:
        - Processes all DATA steps in the program
        - Handles multiple datasets in SET/MERGE statements
        - Generates appropriate IR nodes for each operation
        """
        lowerer = SASLowerer()
        return lowerer.lower_program(ast_root)

    def translate_directory(self, input_dir: Path, output_dir: Path) -> None:
        """Translate all SAS files in input directory to output directory."""
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        sas_files = list(input_dir.glob("*.sas"))

        for sas_file in sas_files:
            try:
                pyspark_code = self.translate_file(sas_file)

                # Write output
                output_file = output_dir / f"{sas_file.stem}.py"
                with open(output_file, "w") as f:
                    f.write(pyspark_code)

                print(f"✓ Translated {sas_file.name} → {output_file.name}")
            except Exception as e:
                print(f"✗ Error translating {sas_file.name}: {e}")


def main(input_dir: Optional[Path] = None, output_dir: Optional[Path] = None) -> None:
    """Main entry point for the translator."""
    print("SAS to PySpark Translator v0.1.0")
    print()

    if input_dir and output_dir:
        translator = SASTranslator()
        translator.translate_directory(input_dir, output_dir)
    else:
        print("Hello from sas2pyspark!")
        print("Usage: from main import main; main(Path('input'), Path('output'))")


if __name__ == "__main__":
    main()
