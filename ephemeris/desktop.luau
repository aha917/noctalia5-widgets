--!nonstrict
-- Ephemeris desktop widget. Plugins cannot draw freely, so render.py
-- (Swiss Ephemeris + pycairo; system python3 or the plugin's .venv) writes the
-- table to a PNG every `interval` seconds and this entry shows it with ui.image.
-- The height depends on the summary, so render.py prints "height=<px>" (in its
-- 900-wide design units) and the image is sized from that.
-- Frames alternate between two file names so the image node sees a new path
-- (and reloads) on every redraw. The names carry a per-instance id, so two
-- placements (or a reload overlapping the old runtime) never share a file.
-- Day buttons (◀ 🗓 ▶) under the date step the shown moment a day back or on,
-- or back to now. Entries cannot overlap the picture, so render.py writes it in
-- three parts (header left of the date, the date corner, the rest; it prints
-- where it cut) and the buttons fill the space under the date corner.
-- Clicking the date opens the "time" panel (time.luau): desktop widgets never
-- get the keyboard, so a typed date and time come back through noctalia.state.
-- Any moment other than now is held (it does not tick on) until 🗓.

local W = 900 -- design width of render.py

local size = noctalia.getConfig("size") or 680
local interval = noctalia.getConfig("interval") or 60
local primary = noctalia.getConfig("primary") or "Fagan/Bradley"
local font = noctalia.getConfig("font") or "0xProto"
local fontSize = noctalia.getConfig("font_size") or 20
local sanskrit = noctalia.getConfig("sanskrit") == true
local order = noctalia.getConfig("order") or "heliocentric"
local signSize = noctalia.getConfig("sign_size") or 31
local planetSize = noctalia.getConfig("planet_size") or 32
local H = 1000 -- until the first render reports the real height
local CUT, DATE_X, DATE_Y = 70, 640, 40 -- header cuts in design units, until render.py reports them
local BUTTON = "#FFFFFF" -- day-button colour
local target = nil -- moment shown: nil = now, a unix time, or typed "DD.MM.YYYY HH:MM"
local lastGood = nil -- target before a typed one, kept in case render.py rejects it
local shift = 0 -- day-button presses not yet applied (render.py moves by whole local days)
local dateText = "" -- the date as drawn, for the time panel

local dir = noctalia.pluginDir()
-- A .venv inside the plugin wins (pip-installed pyswisseph); otherwise the
-- system python3 needs pycairo and pyswisseph.
local python = (dir and noctalia.fileInfo(dir .. "/.venv/bin/python")) and (dir .. "/.venv/bin/python") or "python3"
local dataDir = noctalia.pluginDataDir()
local instance = string.format("%d", noctalia.nowMs())
local frame = 0
local shown, shownRest, shownDate = nil, nil, nil
local busy = false
local pending = false -- a day button was pressed while a render was running
local lastRender = -math.huge

local redraw -- defined below

local function request()
  if busy then pending = true else redraw() end
end

local function step(days)
  if days == 0 then target, shift = nil, 0 else shift = shift + days end
  request()
end

local function openTimePanel()
  noctalia.state.set("ephemeris.picker", { id = instance, date = dateText, n = noctalia.nowMs() })
  noctalia.togglePanel("traditions/ephemeris:time")
end

-- A date and time typed in the panel (only for the widget that opened it).
noctalia.state.watch("ephemeris.goto", function(value)
  if type(value) == "table" and value.id == instance and type(value.text) == "string" then
    lastGood, target, shift = target, value.text, 0
    request()
  end
end)

local function navRow(width, height)
  local function button(glyph, days)
    return ui.row({ width = 24, height = 24, align = "center", justify = "center",
                    onClick = function() step(days) end }, {
      ui.glyph({ name = glyph, size = 16, color = BUTTON }),
    })
  end
  -- Gaps are fixed boxes: ui.spacer always stretches (whatever its width), so
  -- spacers spread the buttons out instead of pushing them right.
  local pad = math.max(0, math.floor(16 * size / W + 0.5) - 4) -- line up with the date's right edge
  local lead = math.max(0, width - pad - 3 * 24 - 4 * 2) -- 4 gaps of 2 between the 5 children
  return ui.row({ width = width, height = height, gap = 2, align = "center" }, {
    ui.box({ width = lead, height = 1, fill = "#00000000" }), -- invisible: a box is filled by default
    button("caret-left-filled", -1),
    button("calendar", 0),
    button("caret-right-filled", 1),
    ui.box({ width = pad, height = 1, fill = "#00000000" }),
  })
end

local function px(units) return math.floor(size * units / W + 0.5) end

local function render()
  local width = size
  local top, rest = px(CUT), px(H) - px(CUT)
  if shown and shownRest and shownDate then
    local left = px(DATE_X)
    local right = width - left
    local dateH = px(DATE_Y)
    desktopWidget.render(ui.column({ gap = 0, width = width }, {
      ui.row({ gap = 0, width = width, height = top }, {
        ui.image({ path = shown, width = left, height = top, fit = "contain" }),
        ui.column({ gap = 0, width = right, height = top }, {
          ui.column({ gap = 0, width = right, height = dateH, onClick = openTimePanel }, {
            ui.image({ path = shownDate, width = right, height = dateH, fit = "contain" }),
          }),
          navRow(right, top - dateH),
        }),
      }),
      ui.image({ path = shownRest, width = width, height = rest, fit = "contain" }),
    }))
  else
    desktopWidget.render(ui.box({ width = width, height = top + rest }))
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

function redraw()
  if busy or not dir or not dataDir then return end
  busy = true
  lastRender = os.time()
  frame = 1 - frame
  local out = dataDir .. "/frame-" .. instance .. "-" .. frame .. ".png"
  local outRest = dataDir .. "/frame-" .. instance .. "-" .. frame .. "-b.png"
  local outDate = dataDir .. "/frame-" .. instance .. "-" .. frame .. "-d.png"
  local req, sh = target, shift
  shift = 0
  local when = req == nil and "" or (type(req) == "number" and string.format("%d", req) or req)
  -- Render at twice the displayed size so it stays sharp on scaled outputs.
  local scale = string.format("%.3f", 2 * size / W)
  noctalia.runAsync({ python, "-I", dir .. "/render.py", out, scale, font, tostring(fontSize), primary, sanskrit and "1" or "0", order,
    tostring(signSize), tostring(planetSize), when, outRest, outDate, tostring(sh) }, function(result)
    busy = false
    if result.exitCode == 0 then
      local h = tonumber(string.match(result.stdout or "", "height=(%d+)"))
      if h then H = h end
      local stdout = result.stdout or ""
      CUT = tonumber(string.match(stdout, "cut=([%d%.]+)")) or CUT
      DATE_X = tonumber(string.match(stdout, "datex=([%d%.]+)")) or DATE_X
      DATE_Y = tonumber(string.match(stdout, "datey=([%d%.]+)")) or DATE_Y
      -- hold the moment drawn (unless it is now): typed text and day steps become a time
      if req ~= nil or sh ~= 0 then target = tonumber(string.match(stdout, "time=(%-?%d+)")) or target end
      dateText = string.match(stdout, "date=([^\n]+)") or dateText
      shown, shownRest, shownDate = out, outRest, outDate
      render()
      sweep()
    else
      noctalia.log("ephemeris: render failed: " .. tostring(result.stderr))
      if type(req) == "string" then target = lastGood end -- a typed time render.py rejected
    end
    if pending then
      pending = false
      redraw()
    end
  end, 20000)
end

function update()
  local now = os.time()
  if now - lastRender >= interval then
    redraw()
  end
end

function onExit()
  if dataDir then
    for f = 0, 1 do
      noctalia.removeFile(dataDir .. "/frame-" .. instance .. "-" .. f .. ".png")
      noctalia.removeFile(dataDir .. "/frame-" .. instance .. "-" .. f .. "-b.png")
      noctalia.removeFile(dataDir .. "/frame-" .. instance .. "-" .. f .. "-d.png")
    end
  end
end

desktopWidget.setWantsSecondTicks(true)
render()
redraw()
