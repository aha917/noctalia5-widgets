--!nonstrict
-- Orrery desktop widget. Plugins cannot draw freely, so render.py
-- (Swiss Ephemeris + pycairo; system python3 or the plugin's .venv) writes the scene to a
-- PNG every `interval` seconds and this entry shows it with ui.image.
-- Frames alternate between two file names so the image node sees a new path
-- (and reloads) on every redraw. The names carry a per-instance id, so two
-- placements (or a reload overlapping the old runtime) never share a file.

local W = 900 -- design width of render.py; its height grows with the font size

local size = noctalia.getConfig("size") or 680
local interval = noctalia.getConfig("interval") or 60
local font = noctalia.getConfig("font") or "0xProto"
local tableFont = noctalia.getConfig("table_font") or "0xProto"
local fontSize = noctalia.getConfig("font_size") or 20
local zodiac = noctalia.getConfig("zodiac") or "tropical"
local zodiacLabel = noctalia.getConfig("zodiac_label")
if zodiacLabel == nil then zodiacLabel = true end
local zodiacSize = noctalia.getConfig("zodiac_font_size") or 20
local order = noctalia.getConfig("order") or "heliocentric"
local function on(key)                      -- bool settings that default to true
  local v = noctalia.getConfig(key)
  return v == nil or v == true
end
local showGC, showGA, showNodes = on("show_gc"), on("show_ga"), on("show_nodes")
-- same formula as canvas_height() in render.py: 10 planet rows plus the optional ones
local rows = 10 + (showGC and 1 or 0) + (showGA and 1 or 0) + (showNodes and 2 or 0)
local H = math.floor(470 + (70 + 25 * rows) * fontSize / 14)

local dir = noctalia.pluginDir()
-- A .venv inside the plugin wins (pip-installed pyswisseph); otherwise the
-- system python3 needs pycairo and pyswisseph.
local python = (dir and noctalia.fileInfo(dir .. "/.venv/bin/python")) and (dir .. "/.venv/bin/python") or "python3"
local dataDir = noctalia.pluginDataDir()
local instance = string.format("%d", noctalia.nowMs())
local frame = 0
local shown = nil
local busy = false
local lastRender = -math.huge

local function render()
  local width = size
  local height = math.floor(size * H / W + 0.5)
  if shown then
    desktopWidget.render(ui.image({ path = shown, width = width, height = height, fit = "contain" }))
  else
    desktopWidget.render(ui.box({ width = width, height = height }))
  end
end

-- Frames of instances that went away without onExit: live ones are rewritten
-- every `interval` seconds, so anything untouched for 10 minutes is an orphan.
local function sweep()
  local names = noctalia.listDir(dataDir)
  if not names then return end
  local now = os.time()
  for _, name in ipairs(names) do
    if name:match("^frame%-.*%.png$") and not name:find(instance, 1, true) then
      local info = noctalia.fileInfo(dataDir .. "/" .. name)
      if info and now - info.mtime > math.max(600, 3 * interval) then
        noctalia.removeFile(dataDir .. "/" .. name)
      end
    end
  end
end

local function redraw()
  if busy or not dir or not dataDir then return end
  busy = true
  frame = 1 - frame
  local out = dataDir .. "/frame-" .. instance .. "-" .. frame .. ".png"
  -- Render at twice the displayed size so it stays sharp on scaled outputs.
  local scale = string.format("%.3f", 2 * size / W)
  noctalia.runAsync({ python, "-I", dir .. "/render.py", out, scale, font, tableFont, tostring(fontSize), zodiac,
    zodiacLabel and "1" or "0", tostring(zodiacSize), order,
    showGC and "1" or "0", showGA and "1" or "0", showNodes and "1" or "0" }, function(result)
    busy = false
    if result.exitCode == 0 then
      shown = out
      render()
      sweep()
    else
      noctalia.log("orrery: render failed: " .. tostring(result.stderr))
    end
  end, 20000)
end

function update()
  local now = os.time()
  if now - lastRender >= interval then
    lastRender = now
    redraw()
  end
end

function onExit()
  if dataDir then
    for f = 0, 1 do noctalia.removeFile(dataDir .. "/frame-" .. instance .. "-" .. f .. ".png") end
  end
end

desktopWidget.setWantsSecondTicks(true)
render()
redraw()
