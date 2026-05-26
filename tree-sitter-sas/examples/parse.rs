/// Example: Parse SAS code and print the AST
use std::io::{self, Read};
use tree_sitter::Parser;

fn main() -> io::Result<()> {
    // Read SAS code from stdin or use example
    let mut code = String::new();

    // Try to read from stdin if available, otherwise use example
    match io::stdin().read_to_string(&mut code) {
        Ok(_) if !code.is_empty() => {},
        _ => {
            code = "data work.test; x = 5; y = a + b * c; run;".to_string();
            println!("No input provided. Using example:\n{}\n", code);
        }
    }

    // Create parser and parse
    let mut parser = Parser::new();
    let language = tree_sitter_sas::language();
    parser.set_language(language)
        .expect("Error loading SAS language");

    match parser.parse(&code, None) {
        Some(tree) => {
            println!("Parse successful!");
            println!("AST:\n{}", tree.root_node());
        }
        None => {
            eprintln!("Parse failed!");
            std::process::exit(1);
        }
    }

    Ok(())
}
