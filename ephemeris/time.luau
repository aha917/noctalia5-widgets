--!nonstrict
-- Ephemeris time pop-up: type a date and time, Enter shows it on the widget
-- that opened the pop-up (desktop.luau sets "ephemeris.picker" and watches
-- "ephemeris.goto"). render.py does the time-zone work.

local opener = nil -- instance id of the widget that opened the pop-up
local draft = ""
local n = 0 -- bumps the input's key so it takes the new text each time it opens
local err = nil
local shownTime = nil -- clock time on the widget when the pop-up opened ("HH:MM")

local show -- defined below

-- "DD.MM.YYYY HH:MM" (a date alone keeps the shown clock time); nil if invalid.
local function normalize(text)
  local d, m, y, h, mi = string.match(text, "^%s*(%d%d?)%.(%d%d?)%.(%d%d%d%d)%s+(%d%d?):(%d%d)%s*$")
  if not d then
    d, m, y = string.match(text, "^%s*(%d%d?)%.(%d%d?)%.(%d%d%d%d)%s*$")
    if not d then return nil end
    h, mi = string.match(shownTime or "", "(%d%d?):(%d%d)")
    h, mi = h or "12", mi or "00"
  end
  d, m, y, h, mi = tonumber(d), tonumber(m), tonumber(y), tonumber(h), tonumber(mi)
  if m < 1 or m > 12 or d < 1 or d > 31 or h > 23 or mi > 59 then return nil end
  return string.format("%02d.%02d.%04d %02d:%02d", d, m, y, h, mi)
end

local function submit(value)
  local text = normalize(value)
  if not text then
    err = "Please write it as DD.MM.YYYY HH:MM"
    draft = value
    show()
    return
  end
  noctalia.state.set("ephemeris.goto", { id = opener, text = text, n = noctalia.nowMs() })
  panel.close()
end

function show()
  panel.render(ui.column({ padding = 14, gap = 8, flexGrow = 1, align = "stretch" }, {
    ui.label({ text = "Show date and time", fontSize = 12, color = "on_surface/0.7" }),
    ui.input({
      key = "when-" .. n,
      value = draft,
      placeholder = "DD.MM.YYYY HH:MM",
      focus = true,
      onChange = function(value) draft = value end,
      onSubmit = submit,
    }),
    ui.label({
      text = err or "Enter to apply · 🗓 on the widget goes back to now",
      fontSize = 10,
      color = err and "error" or "on_surface/0.5",
    }),
  }))
end

function onOpen()
  local p = noctalia.state.get("ephemeris.picker")
  opener = type(p) == "table" and p.id or nil
  draft = type(p) == "table" and p.date or ""
  shownTime = string.match(draft, "(%d%d?:%d%d)")
  n = n + 1
  err = nil
  show()
end

show()
