-- Producer hooks for B738.calc.lua; source preparation, runtime unverified.
dofile("B738.sfp27_core.lua")
local core = B738_sfp27_core
local calc = {}
SFP27DR_active = find_dataref("laminar/B738/sfp27/profile_active")
SFP27DR_input_key = find_dataref("laminar/B738/sfp27/input_key")
SFP27DR_calculated_key = find_dataref("laminar/B738/sfp27/calculated_key")
SFP27DR_n1_valid = find_dataref("laminar/B738/sfp27/n1_valid")
SFP27DR_altitude = find_dataref("sim/flightmodel2/position/pressure_altitude")
SFP27DR_legacy = find_dataref("laminar/B738/73x")
SFP27DR_sfp = find_dataref("laminar/B738/sfp")

local ground_input, ground_input_key = nil, nil
function calc.active()
    return SFP27DR_active == 1
end

local function packs()
    -- Exact original .35 bleed-to-pack invariant, separately for each engine.
    local left = B738DR_bleed_air_1_switch_position ~= 0 and
        (B738DR_l_pack_pos ~= 0 or (B738DR_r_pack_pos ~= 0 and B738DR_isolation_valve_pos ~= 0))
    local right = B738DR_bleed_air_2_switch_position ~= 0 and
        (B738DR_r_pack_pos ~= 0 or (B738DR_l_pack_pos ~= 0 and B738DR_isolation_valve_pos ~= 0))
    return not left, not right
end

local function capture_ground_input()
    local _, assumed = core.rating(B738DR_fms_N1_to_sel, 0)
    local wind = 0
    if B738DR_rw_wind_spd > 0 then
        if B738DR_rw_hdg < 0 or B738DR_rw_wind_dir < 0 then wind = nil
        else wind = B738DR_rw_wind_spd * math.cos(math.rad(B738DR_rw_wind_dir - B738DR_rw_hdg)) end
    end
    local left, right = packs()
    local oat = B738DR_fmc_oat_temp
    if oat == 99 and simDR_radio_height_pilot_ft > 400 then oat = simDR_OAT end
    -- No entered wind retains the original zero-correction FMC convention.
    return {rating = core.rating(B738DR_fms_N1_to_sel, 2),
        selector = B738DR_fms_N1_to_sel,
        weight_t = B738DR_fmc_gw / KGS_LBS, cg_mac = B738DR_fmc_cg,
        flaps = B738DR_fms_takeoff_flaps, runway_condition = B738DR_fmc_rw_cond,
        oat_c = oat, assumed_c = assumed and B738DR_fmc_sel_temp or nil,
        altitude_ft = SFP27DR_altitude,
        headwind_kt = wind, slope_percent = B738DR_rw_slope,
        packs_off_left = left, packs_off_right = right}
end

function calc.n1(altitude, mode)
    local input
    if mode == 3 then
        -- The continuous maximum reference is independent of the ground
        -- snapshot. Its original interface cap is not dispatch performance.
        local left, right = packs()
        input = {rating = core.rating(B738DR_fms_N1_to_sel, mode),
            altitude_ft = math.max(-2000, math.min(10000, SFP27DR_altitude)),
            oat_c = math.max(-50, math.min(60, simDR_OAT)),
            packs_off_left = left, packs_off_right = right}
    else
        if mode == 0 then
            -- Capture the complete producer input once. A later FMS key or
            -- DataRef edit cannot relabel old speeds as a fresh calculation.
            ground_input = capture_ground_input()
            ground_input_key = SFP27DR_input_key
            SFP27DR_n1_valid = 0
        end
        if ground_input == nil then return 0, 0 end
        local rating, assumed = core.rating(ground_input.selector, mode)
        input = {rating = rating, altitude_ft = ground_input.altitude_ft,
            oat_c = ground_input.oat_c,
            assumed_c = assumed and ground_input.assumed_c or nil,
            packs_off_left = ground_input.packs_off_left,
            packs_off_right = ground_input.packs_off_right}
        if input.oat_c == 99 then return 0, 0 end
    end
    local result = core.n1(input)
    if mode == 0 then SFP27DR_n1_valid = result ~= nil and 1 or 0 end
    if result == nil then return 0, 0 end
    if mode == 3 then
        return math.min(1.027, result.left), math.min(1.027, result.right)
    end
    return result.left, result.right
end

function calc.speeds()
    local result = nil
    if ground_input ~= nil and SFP27DR_n1_valid == 1 then result = core.speeds(ground_input) end
    B738DR_fms_v1_calc = result ~= nil and result.v1 or 0
    B738DR_fms_vr_calc = result ~= nil and result.vr or 0
    B738DR_fms_v2_calc = result ~= nil and result.v2 or 0
    B738DR_calc_vspd = 0
    -- A producer snapshot becomes visible only after the numeric outputs.
    SFP27DR_calculated_key = ground_input_key or ""
end

function calc.trim()
    local result = nil
    if ground_input ~= nil then result = core.trim(ground_input) end
    B738DR_trim_calc = result or 0
    B738DR_calc_trim = 0
end

function calc.reset()
    ground_input, ground_input_key = nil, nil
end

raw_table("B738_sfp27_calc")
B738_sfp27_calc = calc
