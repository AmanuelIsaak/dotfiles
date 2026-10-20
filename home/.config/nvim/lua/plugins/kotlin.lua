-- Kotlin LSP from Homebrew (`brew install jetbrains/utils/kotlin-lsp`), not Mason:
-- Mason's registry points at download-cdn.jetbrains.com, which 404s.
local function project_source_for_jar(uri, root)
  local jar, class_path = uri:match("^jar://(.+)!/(.+)%.class$")
  if not jar or not jar:find(root .. "/", 1, true) then
    return nil
  end

  local class_name = class_path:match("([^/]+)$"):match("^[^$]+")
  local source_root = root .. "/sharedLogic/src"
  local matches = vim.fn.systemlist({
    "rg", "-l", "--glob", "*.kt", "-e",
    "\\b(class|interface|object)\\s+" .. class_name .. "\\b", source_root,
  })
  if vim.v.shell_error ~= 0 or #matches ~= 1 then
    return nil
  end
  return matches[1], class_name
end

local function kotlin_definition()
  local client = vim.lsp.get_clients({ bufnr = 0, name = "kotlin_lsp" })[1]
  if not client then
    return vim.lsp.buf.definition()
  end

  local params = vim.lsp.util.make_position_params(0, client.offset_encoding)
  client:request("textDocument/definition", params, function(err, result)
    if err or not result or vim.tbl_isempty(result) then
      -- Kotlin LSP still lacks full commonMain support. Offer a project search.
      return Snacks.picker.grep_word()
    end
    local location = vim.islist(result) and result[1] or result
    local uri = location.uri or location.targetUri
    local root = client.config.root_dir
    local source, class_name
    if root then
      source, class_name = project_source_for_jar(uri, root)
    end
    if source then
      vim.cmd("normal! m'")
      vim.cmd.edit(vim.fn.fnameescape(source))
      for line_number, line in ipairs(vim.api.nvim_buf_get_lines(0, 0, -1, false)) do
        if line:find("class%s+" .. class_name .. "%f[%W]")
          or line:find("interface%s+" .. class_name .. "%f[%W]")
          or line:find("object%s+" .. class_name .. "%f[%W]") then
          vim.api.nvim_win_set_cursor(0, { line_number, 0 })
          break
        end
      end
    else
      vim.lsp.util.show_document(location, client.offset_encoding, { focus = true })
    end
  end, 0)
end

return {
  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
        kotlin_language_server = { enabled = false },
        snyk_ls = { enabled = false },
        kotlin_lsp = {
          mason = false,
          cmd = { "kotlin-lsp", "--stdio" },
          keys = {
            { "gd", kotlin_definition, desc = "Goto Kotlin Definition", has = "definition" },
          },
        },
      },
    },
  },
}
