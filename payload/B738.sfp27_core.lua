-- Source preparation for original 4.05.35 XLua / LuaJIT 5.1.
-- INTENTIONAL FIX: one matched configuration owns 27K, 26K and 24K together.
-- Numeric source tables and manual references are supplied separately.
dofile("B738.sfp27_data.lua")
local data = B738_sfp27_data
local core = {profile = data.profile, version = "0.1.0-beta.4"}

local function finite(n)
    return type(n) == "number" and n == n and n > -math.huge and n < math.huge
end

local function bracket(axis, value)
    if not finite(value) or value < axis[1] or value > axis[#axis] then return nil end
    for i = 1, #axis do
        if value == axis[i] then return i, i, 0 end
        if value < axis[i] then
            return i - 1, i, (value - axis[i - 1]) / (axis[i] - axis[i - 1])
        end
    end
end

local function mix(a, b, fraction)
    if not finite(a) or not finite(b) then return nil end
    return a + (b - a) * fraction
end

local function column(grid, index, y)
    local lo, hi, f = bracket(grid.y, y)
    if lo == nil then return nil end
    return mix(grid.cells[lo][index], grid.cells[hi][index], f)
end

local function interpolate(grid, x, y, offset, axis)
    axis, offset = axis or grid.x, offset or 0
    local lo, hi, f = bracket(axis, x)
    if lo == nil then return nil end
    return mix(column(grid, offset + lo, y), column(grid, offset + hi, y), f)
end

local function vector(axis, values, value)
    local lo, hi, f = bracket(axis, value)
    if lo == nil then return nil end
    return mix(values[lo], values[hi], f)
end

function core.vref(weight_t)
    -- Landing references, independent of takeoff rating/assumed temperature.
    -- Keep unrounded values here; the publishing adapter owns integer knots.
    local landing = data.landing_vref
    local ref30 = vector(landing.weight_t, landing.f30, weight_t)
    local ref40 = vector(landing.weight_t, landing.f40, weight_t)
    local ref15 = vector(landing.weight_t, landing.f15, weight_t)
    if ref30 == nil or ref40 == nil or ref15 == nil then return nil, nil, nil end
    return ref30, ref40, ref15
end

function core.supported(variant, legacy_variant, sfp)
    -- Native passenger -800 or native Zibo -800 only. BBJ/other IDs excluded.
    return sfp == 1 and (variant == 0 or (variant == -1 and legacy_variant == 0))
end

function core.rating(selector, mode)
    if mode == 3 then return 27, false end
    if not finite(selector) or selector ~= math.floor(selector) or selector < 1 or selector > 6 then
        return nil
    end
    local index = selector > 3 and selector - 3 or selector
    -- FCOM11.32.3: fixed derate remains the normal ground takeoff limit,
    -- including ATM+fixed. Restoring ATM alone never discards that ceiling.
    return ({27, 26, 24})[index], selector > 3 and mode ~= 1 and mode ~= 2
end

function core.n1(input)
    local rating = data.ratings[input.rating]
    if rating == nil or not finite(input.oat_c) or not finite(input.altitude_ft) then
        return nil, "INPUT"
    end
    local percent, bleed
    if input.assumed_c == nil then
        percent = interpolate(rating.n1, input.altitude_ft, input.oat_c)
        bleed = vector(rating.n1.x, rating.packs_off, input.altitude_ft)
    else
        if not finite(input.assumed_c) or input.assumed_c <= input.oat_c then return nil, "ATM_OAT" end
        -- The first maximum-ATM row explicitly says 'and below'. It does not
        -- authorize extrapolating the independent temperature-difference grid.
        local oat_max_lookup = math.max(input.oat_c, rating.atm_max.y[1])
        local maximum = interpolate(rating.atm_max, input.altitude_ft, oat_max_lookup)
        local minimum = vector(rating.atm_n1.x, rating.atm_min, input.altitude_ft)
        if maximum == nil or minimum == nil then return nil, "ATM_CELL" end
        if input.assumed_c > maximum or input.assumed_c < minimum then return nil, "ATM_LIMIT" end
        percent = interpolate(rating.atm_n1, input.altitude_ft, input.assumed_c)
        local correction = interpolate(rating.atm_delta, input.oat_c, input.assumed_c - input.oat_c)
        if percent == nil or correction == nil then return nil, "ATM_CELL" end
        percent, bleed = percent - correction, 1
    end
    if percent == nil or bleed == nil then return nil, "N1_CELL" end
    local left = percent + (input.packs_off_left and bleed or 0)
    local right = percent + (input.packs_off_right and bleed or 0)
    -- 108 is the original plugin interface bound, never a substitute table.
    if left <= 0 or right <= 0 or left > 108 or right > 108 then return nil, "N1_INTERFACE" end
    return {left = left / 100, right = right / 100, rating = input.rating}
end

local flap_columns = {[1] = 0, [5] = 3, [10] = 6, [15] = 9, [25] = 12}
local altitude_axis = {-2000, 0, 2000, 4000, 6000, 8000, 10000}
local slope_axis = {-2, -1, 0, 1, 2}
local wind_axis = {-15, -10, -5, 0, 10, 20, 30, 40}

function core.speeds(input)
    local rating = data.ratings[input.rating]
    local offset = flap_columns[input.flaps]
    if rating == nil or offset == nil or (input.runway_condition ~= 0 and input.runway_condition ~= 1) then
        return nil, "CONFIGURATION"
    end
    local table_set = input.runway_condition == 0 and rating.dry or rating.wet
    -- PI.257.2: speed adjustments use assumed temperature for reduced-thrust
    -- takeoff, while V1(MCG) always uses actual OAT.
    local speed_temperature = input.oat_c
    if input.assumed_c ~= nil then
        if core.n1(input) == nil then return nil, "ATM_INPUT" end
        speed_temperature = input.assumed_c
    end
    local v1 = column(table_set.base, offset + 1, input.weight_t)
    local vr = column(table_set.base, offset + 2, input.weight_t)
    local v2 = column(table_set.base, offset + 3, input.weight_t)
    local adj1 = interpolate(table_set.adjust, input.altitude_ft, speed_temperature, 0, altitude_axis)
    local adjr = interpolate(table_set.adjust, input.altitude_ft, speed_temperature, 7, altitude_axis)
    local adj2 = interpolate(table_set.adjust, input.altitude_ft, speed_temperature, 14, altitude_axis)
    local slope = interpolate(table_set.slope_wind, input.slope_percent, input.weight_t, 0, slope_axis)
    local wind = interpolate(table_set.slope_wind, input.headwind_kt, input.weight_t, 5, wind_axis)
    local mcg = interpolate(table_set.mcg, input.altitude_ft, input.oat_c)
    if v1 == nil or vr == nil or v2 == nil or adj1 == nil or adjr == nil or adj2 == nil or
       slope == nil or wind == nil or mcg == nil then return nil, "SPEED_CELL" end
    v1, vr, v2 = v1 + adj1 + slope + wind, vr + adjr, v2 + adj2
    -- Manual: V1 not above VR; check V1(MCG). PI.257 allows increased VR/V2
    -- only with applicable field-length/certified speed-increase evidence.
    -- That evidence is absent from v0.1; keep this combination unavailable.
    vr, v2 = math.floor(vr), math.floor(v2)
    v1 = math.max(math.floor(math.min(v1, vr)), math.ceil(mcg))
    if v1 > vr or vr > v2 then return nil, "SPEED_ORDER" end
    return {v1 = v1, vr = vr, v2 = v2, mcg = mcg}
end

function core.trim(input)
    local rating = data.ratings[input.rating]
    if rating == nil or flap_columns[input.flaps] == nil then return nil, "CONFIGURATION" end
    local grid = (input.flaps == 1 or input.flaps == 5) and rating.trim.low_flaps or rating.trim.high_flaps
    local trim = interpolate(grid, input.cg_mac, input.weight_t)
    if trim == nil then return nil, "TRIM_CELL" end
    return math.floor(trim * 100 + .5) / 100
end

-- XLua dofile does not reliably propagate a returned table into the caller.
raw_table("B738_sfp27_core")
B738_sfp27_core = core
