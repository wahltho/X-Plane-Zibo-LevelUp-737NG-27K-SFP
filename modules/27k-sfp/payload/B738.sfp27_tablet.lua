-- Guard the unsupported dispatch/optimizer surface in either install order.
local guard = {}
local wrappers = {}
local last_active = nil
SFP27DR_active = find_dataref("laminar/B738/sfp27/profile_active")

local function active() return SFP27DR_active == 1 end

local function clear()
    -- Cancel the Lua wait/parse state of a pre-profile external JBR request.
    -- An external process may still finish, but its result is no longer accepted.
    jbr_find_rwy_timer = 0
    perf_takeoff_err, perf_takeoff_rating, perf_takeoff_windshear = 1, 0, 0
    perf_takeoff_full_valid, perf_takeoff_atm_valid = 0, 0
    perf_takeoff_full_rating, perf_takeoff_atm_rating = 0, 0
    perf_takeoff_full_n1, perf_takeoff_atm_n1, perf_takeoff_n1 = 0, 0, 0
    perf_takeoff_full_v1, perf_takeoff_full_vr, perf_takeoff_full_v2 = 0, 0, 0
    perf_takeoff_atm_v1, perf_takeoff_atm_vr, perf_takeoff_atm_v2 = 0, 0, 0
    perf_takeoff_v1, perf_takeoff_vr, perf_takeoff_v2 = 0, 0, 0
    perf_takeoff_atm_seltemp, perf_takeoff_seltemp, perf_takeoff_max_wt = 0, 0, 0
    perf_takeoff_vref40, perf_takeoff_flaps, perf_takeoff_trim = 0, 0, -1
    B738DR_atm_valid = 0
end

local function page_guard(original, ...)
    if not active() then return original(...) end
    clear()
    page, max_page = 1, 1
    for i = 0, 15 do
        line[i], line_c[i], line_s[i], line_g[i] = "", "", "", ""
        B738DR_tab_perf_manip[i] = 0
        if i < 10 then B738DR_tab_line_manip[i] = 0 end
    end
    line_c[0] = "        PERFORMANCE TAKEOFF"
    line[3] = " 27K SFP PERFORMANCE UNAVAILABLE"
    line[5] = " USE FMC TAKEOFF REF"
    line[7] = " DISPATCH DATA REQUIRED"
end

local function command_guard(original, ...)
    if active() then clear(); return end
    return original(...)
end

local function wrap(name, current, handler)
    if current == nil or current == wrappers[name] then return current end
    -- Capture each generation by value: wrapping a later Tablet adapter must
    -- not make an older wrapper call back into that adapter recursively.
    local original = current
    local wrapped = function(...) return handler(original, ...) end
    wrappers[name] = wrapped
    return wrapped
end

function guard.ensure()
    local selected = active()
    if last_active ~= selected and cat == CAT_PERF_TAKEOFF then display_update = 1 end
    last_active = selected
    page_perf_takeof = wrap("page", page_perf_takeof, page_guard)
    cmd_perf_takeoff = wrap("cmd", cmd_perf_takeoff, command_guard)
    cmd_perf_takeoff2 = wrap("cmd2", cmd_perf_takeoff2, command_guard)
    jbr_opt_calculate = wrap("calculate", jbr_opt_calculate, command_guard)
    -- Original after_physics calls this async-result owner AFTER the guard.
    -- Wrap every generation, including a later performance-adapter replacement.
    jbr_opt = wrap("result", jbr_opt, command_guard)
    if active() then clear() end
end

raw_table("B738_sfp27_tablet")
B738_sfp27_tablet = guard
