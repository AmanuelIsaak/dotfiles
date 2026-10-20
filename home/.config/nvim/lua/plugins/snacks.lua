-- Snacks notifier (LazyVim already ships snacks.nvim; this tunes the notifications)
-- <leader>n  notification history   <leader>un  dismiss all
return {
  "folke/snacks.nvim",
  opts = {
    notifier = {
      enabled = true,
      timeout = 3000,
      style = "fancy", -- "compact" | "fancy" | "minimal"
      top_down = true,
    },
  },
}
