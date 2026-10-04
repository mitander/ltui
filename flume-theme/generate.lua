-- Personal Pantheon export. Run with FLUME_RUNTIME and FLUME_TRACKER_OUTPUT set.
-- Consume canonical palette metadata; never load Flume's compiler or activate it.
local runtime = assert(vim.env.FLUME_RUNTIME, "FLUME_RUNTIME is required")
local output = assert(vim.env.FLUME_TRACKER_OUTPUT, "FLUME_TRACKER_OUTPUT is required")
vim.opt.runtimepath:prepend(runtime)
local palettes = require("flume.palette")
local roles = {
    text = "text", text_subtle = "fg", text_muted = "syntax_comment",
    border = "border", border_subtle = "border_variant",
    accent = "accent", accent_secondary = "syntax_keyword", accent_tertiary = "cyan",
    success = "success", warning = "warning", error = "error",
    status_triage = "warning", status_started = "warning", status_unstarted = "accent",
    status_backlog = "syntax_comment", status_completed = "success", status_canceled = "syntax_comment",
    team = "accent", project = "syntax_type", initiative = "syntax_keyword", label = "cyan",
    blocked = "error", blocking = "warning", priority_urgent = "error",
}
local variables = {
    border = "border", border_focus = "border_focused", border_detail = "cyan",
    modal_bg = "surface", cursor = "element_active",
    scrollbar = "border_variant", scrollbar_hover = "border", scrollbar_active = "border_focused",
    scrollbar_background = "bg", selection_background = "accent", selection_foreground = "on_accent",
}
local fields = {
    primary = "accent", secondary = "syntax_keyword", accent = "cyan",
    background = "bg", surface = "surface_alt", panel = "surface", foreground = "text",
    success = "success", warning = "warning", error = "error",
}
local function resolve(mapping, colors)
    local result = {}
    for key, role in pairs(mapping) do
        result[key] = assert(colors[role], "missing palette role: " .. role)
    end
    return result
end
vim.fn.mkdir(output, "p")
for _, schema in ipairs(palettes.schema_order) do
    local meta = palettes.get(schema)
    local theme = resolve(fields, meta.colors)
    theme.name = meta.integration_name
    theme.dark = meta.appearance == "dark"
    theme.roles = resolve(roles, meta.colors)
    theme.variables = resolve(variables, meta.colors)
    theme.variables.overlay = theme.dark and "black 40%" or "black 15%"
    vim.fn.writefile({ vim.json.encode(theme) }, output .. "/" .. theme.name .. ".json")
end
vim.cmd("qa!")
