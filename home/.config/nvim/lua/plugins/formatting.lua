-- Format on save (LazyVim's conform.nvim). Toggle with <leader>uf (buffer) / <leader>uF (global).
-- prettier prefers the project's node_modules copy, so Svelte formats with the
-- project's prettier-plugin-svelte. Kotlin, Rust and prettier come from Homebrew;
-- the rest from Mason.
return {
  {
    "stevearc/conform.nvim",
    opts = {
      formatters_by_ft = {
        python = { "ruff_organize_imports", "ruff_format" },
        javascript = { "prettier" },
        javascriptreact = { "prettier" },
        typescript = { "prettier" },
        typescriptreact = { "prettier" },
        svelte = { "prettier" },
        css = { "prettier" },
        html = { "prettier" },
        json = { "prettier" },
        swift = { "swiftformat" },
        kotlin = { "ktlint" },
        go = { "goimports", "gofumpt" },
        rust = { "rustfmt" },
        lua = { "stylua" },
      },
    },
  },
  {
    "mason-org/mason.nvim",
    opts = { ensure_installed = { "ruff", "swiftformat", "goimports", "gofumpt", "stylua" } },
  },
}
