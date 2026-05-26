/// Tree-sitter SAS language binding
///
/// This crate provides a compiled Tree-sitter parser for the SAS language.
/// It can be used directly in Rust or through Python via ctypes/cffi.

use tree_sitter::Language;

extern "C" {
    fn tree_sitter_sas() -> Language;
}

/// Get the Tree-sitter language for SAS
pub fn language() -> Language {
    unsafe { tree_sitter_sas() }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tree_sitter::Parser;

    #[test]
    fn test_parse_simple_data_step() {
        let mut parser = Parser::new();
        parser.set_language(language()).expect("Error loading SAS language");

        let code = "data test; x = 5; run;";
        let tree = parser.parse(code, None);

        assert!(tree.is_some());
        let tree = tree.unwrap();
        assert_eq!(tree.root_node().kind(), "source_file");
    }

    #[test]
    fn test_parse_expression() {
        let mut parser = Parser::new();
        parser.set_language(language()).expect("Error loading SAS language");

        let code = "data test; y = a + b * c; run;";
        let tree = parser.parse(code, None);

        assert!(tree.is_some());
    }
}
