package com.lushprojects.circuitjs1.client;

import java.util.ArrayList;
import java.util.List;

/**
 * Small recursive-descent parser for Arduino-Lite C.
 *
 * Grammar (subset):
 * program      := (global_decl | function_decl)*
 * global_decl  := 'int' IDENT ('=' expr)? ';'
 * function_decl:= 'void' IDENT '(' ')' '{' stmt* '}'
 * stmt         := block | var_decl | if | while | return | expr_stmt
 * block        := '{' stmt* '}'
 * var_decl     := ('int' | 'bool') IDENT ('=' expr)? ';'
 * if           := 'if' '(' expr ')' stmt ('else' stmt)?
 * while        := 'while' '(' expr ')' stmt
 * return       := 'return' expr? ';'
 * expr_stmt    := expr ';' | IDENT '=' expr ';'
 * expr         := assignment
 * assignment   := logical_or ( '=' assignment )?
 * logical_or   := logical_and ( '||' logical_and )*
 * logical_and  := equality ( '&&' equality )*
 * equality     := relational ( ('=='|'!=') relational )*
 * relational   := add ( ('<'|'>'|'<='|'>=') add )*
 * add          := mul ( ('+'|'-') mul )*
 * mul          := unary ( ('*'|'/'|'%') unary )*
 * unary        := ('!'|'-')? primary
 * primary      := NUMBER | 'true' | 'false' | IDENT | IDENT '(' args? ')' | '(' expr ')'
 *
 * Very small tokenizer implemented inline.
 */
public class ArduinoParser {

    private final String input;
    private int pos;
    private Token cur;

    private enum TokenType { IDENT, NUMBER, SYMBOL, EOF, KEYWORD }
    private static class Token {
        TokenType type;
        String text;
        Token(TokenType t, String s) { type = t; text = s; }
        public String toString() { return type + ":" + text; }
    }

    // keywords
    private static final String[] KEYWORDS = {
        "int","void","if","else","while","return","true","false","bool"
    };

    private ArduinoParser(String input) {
        this.input = input;
        this.pos = 0;
        next();
    }

    public static AST.Program parseProgram(String src) throws ParseException {
        ArduinoParser p = new ArduinoParser(src);
        return p.parseProgramInternal();
    }

    private AST.Program parseProgramInternal() throws ParseException {
        AST.Program prog = new AST.Program();
        while (cur.type != TokenType.EOF) {
            if (accept("int") || accept("bool")) {
                // global var
                Token prev = previous();
                String type = prev.text;
                Token name = expectIdent("expected global variable name");
                AST.VarDecl g = null;
                if (accept("=")) {
                    AST.Expr e = parseExpression();
                    expect(";","expected ';' after global decl");
                    g = new AST.VarDecl(name.text, e);
                } else {
                    expect(";","expected ';' after global decl");
                    g = new AST.VarDecl(name.text, null);
                }
                prog.globals.add(g);
            } else if (accept("void")) {
                Token name = expectIdent("expected function name");
                expect("(","expected '(' after function name");
                expect(")", "expected ')'");
                expect("{","expected '{' function body");
                AST.FunctionDecl f = new AST.FunctionDecl(name.text);
                while (!accept("}")) {
                    AST.Stmt s = parseStmt();
                    if (s != null) f.body.add(s);
                }
                prog.functions.add(f);
            } else {
                throw new ParseException("Unexpected token: " + cur);
            }
        }
        return prog;
    }

    // ---------- statements ----------
    private AST.Stmt parseStmt() throws ParseException {
        if (accept("{")) {
            AST.StmtBlock block = new AST.StmtBlock();
            while (!accept("}")) {
                block.stmts.add(parseStmt());
            }
            return block;
        }
        if (accept("int") || accept("bool")) {
            Token prev = previous();
            Token name = expectIdent("expected var name");
            AST.Expr init = null;
            if (accept("=")) init = parseExpression();
            expect(";","expected ';' after var decl");
            return new AST.StmtVarDecl(name.text, init);
        }
        if (accept("if")) {
            expect("(","expected '(' after if");
            AST.Expr cond = parseExpression();
            expect(")","expected ')'");
            AST.Stmt thenS = parseStmt();
            AST.Stmt elseS = null;
            if (accept("else")) elseS = parseStmt();
            return new AST.StmtIf(cond, thenS, elseS);
        }
        if (accept("while")) {
            expect("(", "expected '(' after while");
            AST.Expr cond = parseExpression();
            expect(")", "expected ')'");
            AST.Stmt body = parseStmt();
            return new AST.StmtWhile(cond, body);
        }
        if (accept("return")) {
            AST.Expr e = null;
            if (!accept(";")) {
                e = parseExpression();
                expect(";","expected ';' after return");
            }
            return new AST.StmtReturn(e);
        }
        // assignment or expr stmt
        if (cur.type == TokenType.IDENT) {
            Token name = cur;
            Token next = peekToken();
            if (next != null && "=".equals(next.text)) {
                // assignment
                next(); // consume name
                expect("=","expected '=' in assignment");
                AST.Expr e = parseExpression();
                expect(";","expected ';' after assignment");
                return new AST.StmtAssign(name.text, e);
            }
        }
        AST.Expr e = parseExpression();
        expect(";","expected ';' after expression");
        return new AST.StmtExpr(e);
    }

    // ---------- expressions ----------
    private AST.Expr parseExpression() throws ParseException {
        return parseAssignment();
    }

    private AST.Expr parseAssignment() throws ParseException {
    AST.Expr left = parseLogicalOr();

    if (accept("=")) {
        // Prevent assignment inside expressions
        throw new ParseException("Assignment must be in a statement, not inside an expression.");
    }
    return left;
    }

    private AST.Expr parseLogicalOr() throws ParseException {
        AST.Expr expr = parseLogicalAnd();
        while (accept("||")) {
            AST.Expr right = parseLogicalAnd();
            expr = new AST.ExprBinary("||", expr, right);
        }
        return expr;
    }

    private AST.Expr parseLogicalAnd() throws ParseException {
        AST.Expr expr = parseEquality();
        while (accept("&&")) {
            AST.Expr right = parseEquality();
            expr = new AST.ExprBinary("&&", expr, right);
        }
        return expr;
    }

    private AST.Expr parseEquality() throws ParseException {
        AST.Expr expr = parseRelational();
        while (true) {
            if (accept("==")) { AST.Expr r = parseRelational(); expr = new AST.ExprBinary("==", expr, r); continue; }
            if (accept("!=")) { AST.Expr r = parseRelational(); expr = new AST.ExprBinary("!=", expr, r); continue; }
            break;
        }
        return expr;
    }

    private AST.Expr parseRelational() throws ParseException {
        AST.Expr expr = parseAdd();
        while (true) {
            if (accept("<=")) { AST.Expr r = parseAdd(); expr = new AST.ExprBinary("<=", expr, r); continue; }
            if (accept(">=")) { AST.Expr r = parseAdd(); expr = new AST.ExprBinary(">=", expr, r); continue; }
            if (accept("<")) { AST.Expr r = parseAdd(); expr = new AST.ExprBinary("<", expr, r); continue; }
            if (accept(">")) { AST.Expr r = parseAdd(); expr = new AST.ExprBinary(">", expr, r); continue; }
            break;
        }
        return expr;
    }

    private AST.Expr parseAdd() throws ParseException {
        AST.Expr expr = parseMul();
        while (true) {
            if (accept("+")) { AST.Expr r = parseMul(); expr = new AST.ExprBinary("+", expr, r); continue; }
            if (accept("-")) { AST.Expr r = parseMul(); expr = new AST.ExprBinary("-", expr, r); continue; }
            break;
        }
        return expr;
    }

    private AST.Expr parseMul() throws ParseException {
        AST.Expr expr = parseUnary();
        while (true) {
            if (accept("*")) { AST.Expr r = parseUnary(); expr = new AST.ExprBinary("*", expr, r); continue; }
            if (accept("/")) { AST.Expr r = parseUnary(); expr = new AST.ExprBinary("/", expr, r); continue; }
            if (accept("%")) { AST.Expr r = parseUnary(); expr = new AST.ExprBinary("%", expr, r); continue; }
            break;
        }
        return expr;
    }

    private AST.Expr parseUnary() throws ParseException {
        if (accept("!")) {
            AST.Expr e = parseUnary(); return new AST.ExprUnary("!", e);
        }
        if (accept("-")) {
            AST.Expr e = parseUnary(); return new AST.ExprUnary("-", e);
        }
        return parsePrimary();
    }

    private AST.Expr parsePrimary() throws ParseException {
        if (accept("(")) {
            AST.Expr e = parseExpression();
            expect(")", "expected ')'");
            return e;
        }
        if (cur.type == TokenType.NUMBER) {
            int v = Integer.parseInt(cur.text);
            next();
            return new AST.ExprLiteral(v);
        }
        if (accept("true")) { return new AST.ExprBool(true); }
        if (accept("false")) { return new AST.ExprBool(false); }
        if (cur.type == TokenType.IDENT) {
            Token name = cur; next();
            if (accept("(")) {
                AST.ExprCall call = new AST.ExprCall(name.text);
                if (!accept(")")) {
                    call.args.add(parseExpression());
                    while (accept(",")) call.args.add(parseExpression());
                    expect(")","expected ')'");
                }
                return call;
            } else {
                return new AST.ExprVar(name.text);
            }
        }
        throw new ParseException("Unexpected token in primary: " + cur);
    }

    // ---------- tokenizer & helpers ----------
    private void next() {
        skipWhitespaceAndComments();
        if (pos >= input.length()) { cur = new Token(TokenType.EOF, "<EOF>"); return; }
        char c = input.charAt(pos);
        if (isIdentifierStart(c)) {
            int s = pos;
            pos++;
            while (pos < input.length() && isIdentifierPart(input.charAt(pos))) pos++;
            String word = input.substring(s,pos);
            if (isKeyword(word)) cur = new Token(TokenType.KEYWORD, word);
            else cur = new Token(TokenType.IDENT, word);
            return;
        }
        if (isDigit(c)) {
            int s = pos; pos++;
            while (pos < input.length() && isDigit(input.charAt(pos))) pos++;
            cur = new Token(TokenType.NUMBER, input.substring(s,pos));
            return;
        }
        // multi-char symbols
        String two = (pos + 1 < input.length()) ? input.substring(pos, pos+2) : null;
        if (two != null && (two.equals("==")||two.equals("!=")||two.equals(">=")||two.equals("<=")||two.equals("||")||two.equals("&&"))) {
            cur = new Token(TokenType.SYMBOL, two); pos += 2; return;
        }
        // single char symbols
        cur = new Token(TokenType.SYMBOL, Character.toString(c)); pos++;
    }

    private Token peekToken() {
        int old = pos;
        Token oldCur = cur;
        next();
        Token p = cur;
        pos = old;
        cur = oldCur;
        return p;
    }

    private Token previous() { return cur; }

    private boolean accept(String s) {
        if (cur == null) return false;
        if ((cur.type == TokenType.KEYWORD || cur.type == TokenType.IDENT || cur.type == TokenType.SYMBOL) && cur.text.equals(s)) {
            next(); return true;
        }
        return false;
    }

    private void expect(String s, String msg) throws ParseException {
        if (!accept(s)) throw new ParseException(msg + " saw: " + cur);
    }

    private Token expectIdent(String msg) throws ParseException {
        if (cur.type == TokenType.IDENT) { Token t = cur; next(); return t; }
        throw new ParseException(msg + " saw: " + cur);
    }

    private boolean isKeyword(String w) {
        for (String k : KEYWORDS) if (k.equals(w)) return true;
        return false;
    }

    private void skipWhitespaceAndComments() {
        while (pos < input.length()) {
            char c = input.charAt(pos);
            if (Character.isWhitespace(c)) { pos++; continue; }
            if (c == '/' && pos + 1 < input.length()) {
                char c2 = input.charAt(pos+1);
                if (c2 == '/') { pos+=2; while (pos < input.length() && input.charAt(pos) != '\n') pos++; continue; }
                if (c2 == '*') { pos+=2; while (pos+1 < input.length() && !(input.charAt(pos)=='*' && input.charAt(pos+1)=='/')) pos++; pos+=2; continue; }
            }
            break;
        }
    }

    private boolean isIdentifierStart(char c) { return Character.isLetter(c) || c == '_'; }
    private boolean isIdentifierPart(char c) { return Character.isLetterOrDigit(c) || c == '_'; }
    private boolean isDigit(char c) { return c >= '0' && c <= '9'; }

    public static class ParseException extends Exception {
        public ParseException(String msg) { super(msg); }
    }
}
