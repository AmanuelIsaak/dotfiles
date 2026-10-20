-- Tokyo Night follows Neovim's light and dark background.
-- The colorscheme follows 'background', which Neovim updates when the
-- terminal reports a light/dark change.
return {
  { "folke/tokyonight.nvim", opts = { style = "night", light_style = "day" } },
  { "LazyVim/LazyVim", opts = { colorscheme = "tokyonight" } },
}
