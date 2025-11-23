package com.lushprojects.circuitjs1.client;

import java.util.ArrayList;
import java.util.List;

public class AST {

    // ---------- Program ----------
    public static class Program {
        public final List<VarDecl> globals = new ArrayList<>();
        public final List<FunctionDecl> functions = new ArrayList<>();
    }

    // ---------- Declarations ----------
    public static class VarDecl {
        public final String name;
        public final Expr init;
        public VarDecl(String name, Expr init) {
            this.name = name;
            this.init = init;
        }
    }

    public static class FunctionDecl {
        public final String name;
        public final List<Stmt> body = new ArrayList<>();
        public FunctionDecl(String name) {
            this.name = name;
        }
    }

    // ---------- Statements ----------
    public static abstract class Stmt { }

    public static class StmtBlock extends Stmt {
        public final List<Stmt> stmts = new ArrayList<>();
    }

    public static class StmtVarDecl extends Stmt {
        public final String name;
        public final Expr init;
        public StmtVarDecl(String name, Expr init) {
            this.name = name;
            this.init = init;
        }
    }

    public static class StmtIf extends Stmt {
        public final Expr cond;
        public final Stmt thenStmt;
        public final Stmt elseStmt;
        public StmtIf(Expr cond, Stmt thenStmt, Stmt elseStmt) {
            this.cond = cond;
            this.thenStmt = thenStmt;
            this.elseStmt = elseStmt;
        }
    }

    public static class StmtWhile extends Stmt {
        public final Expr cond;
        public final Stmt body;
        public StmtWhile(Expr cond, Stmt body) {
            this.cond = cond;
            this.body = body;
        }
    }

    public static class StmtReturn extends Stmt {
        public final Expr value;
        public StmtReturn(Expr v) {
            this.value = v;
        }
    }

    public static class StmtAssign extends Stmt {
        public final String name;
        public final Expr value;
        public StmtAssign(String name, Expr value) {
            this.name = name;
            this.value = value;
        }
    }

    public static class StmtExpr extends Stmt {
        public final Expr expr;
        public StmtExpr(Expr e) { this.expr = e; }
    }

    // ---------- Expressions ----------
    public static abstract class Expr { }

    public static class ExprLiteral extends Expr {
        public final int value;
        public ExprLiteral(int v) { this.value = v; }
    }

    public static class ExprBool extends Expr {
        public final boolean value;
        public ExprBool(boolean v) { this.value = v; }
    }

    public static class ExprVar extends Expr {
        public final String name;
        public ExprVar(String n) { this.name = n; }
    }

    public static class ExprCall extends Expr {
        public final String name;
        public final List<Expr> args = new ArrayList<>();
        public ExprCall(String name) { this.name = name; }
    }

    public static class ExprBinary extends Expr {
        public final String op;
        public final Expr left;
        public final Expr right;
        public ExprBinary(String op, Expr l, Expr r) {
            this.op = op;
            this.left = l;
            this.right = r;
        }
    }

    public static class ExprUnary extends Expr {
        public final String op;
        public final Expr expr;
        public ExprUnary(String op, Expr expr) {
            this.op = op;
            this.expr = expr;
        }
    }
}
