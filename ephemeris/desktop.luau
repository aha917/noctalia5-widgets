--!nonstrict
-- Ephemeris desktop widget. Plugins cannot draw freely, so render.py
-- (Swiss Ephemeris + pycairo; system python3 or the plugin's .venv) writes the
-- table to a PNG every `interval` seconds and this entry shows it with ui.image.
-- The height depends on the summary, so render.py prints "height=<px>" (in its
-- 900-wide design units) and the image is sized from that.
-- Frames alternate between two file names so the image node sees a new path
-- (and reloads) on every redraw. The names carry a per-instance id, so two
-- placements (or a reload overlapping the old runtime) never share a file.

local W = 900 -- design width of render.py

local size = noctalia.getConfig("size") or 680
local interval = noctalia.getConfig("interval") or 60
local primary = noctalia.getConfig("primary") or "Fagan/Bradley"
local font = noctalia.getConfig("font") or "0xProto"
local fontSize = noctalia.getConfig("font_size") or 20
local H = 1000 -- until the first render reports the real height

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
  noctalia.runAsync({ python, "-I", dir .. "/render.py", out, scale, font, tostring(fontSize), primary }, function(result)
    busy = false
    if result.exitCode == 0 then
      local h = tonumber(string.match(result.stdout or "", "height=(%d+)"))
      if h then H = h end
      shown = out
      render()
      sweep()
    else
      noctalia.log("ephemeris: render failed: " .. tostring(result.stderr))
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
