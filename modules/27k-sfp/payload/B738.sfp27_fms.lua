-- FMC profile/persistence/publication integration. Original cfg slot 164 owns SFP.
dofile("B738.sfp27_core.lua")
local core = B738_sfp27_core
local fms = {}
local automatic = {}
local last_key = nil

SFP27DR_active = create_dataref("laminar/B738/sfp27/profile_active", "number")
SFP27DR_input_key = create_dataref("laminar/B738/sfp27/input_key", "string")
SFP27DR_calculated_key = create_dataref("laminar/B738/sfp27/calculated_key", "string")
SFP27DR_n1_valid = create_dataref("laminar/B738/sfp27/n1_valid", "number")
SFP27DR_altitude = find_dataref("sim/flightmodel2/position/pressure_altitude")
SFP27DR_groundspeed = find_dataref("sim/flightmodel/position/groundspeed")
SFP27DR_on_ground = find_dataref("sim/flightmodel2/gear/on_ground")
SFP27DR_bleed1 = find_dataref("laminar/B738/toggle_switch/bleed_air_1_pos")
SFP27DR_bleed2 = find_dataref("laminar/B738/toggle_switch/bleed_air_2_pos")
SFP27DR_pack1 = find_dataref("laminar/B738/air/l_pack_pos")
SFP27DR_pack2 = find_dataref("laminar/B738/air/r_pack_pos")
SFP27DR_isolation = find_dataref("laminar/B738/air/isolation_valve_pos")
SFP27DR_der_full = find_dataref("laminar/B738/engine/calc/thr_takeoff_der_full_N1")
SFP27DR_active = 0
SFP27DR_input_key, SFP27DR_calculated_key = "", ""
SFP27DR_n1_valid = 0

local function ground_editable()
    return SFP27DR_groundspeed < 42 and
        (SFP27DR_on_ground[0] == 1 or SFP27DR_on_ground[1] == 1 or SFP27DR_on_ground[2] == 1)
end

local function set_speed(name, value)
    if name == "v1" then v1_set, B738DR_fms_v1_set = value, tonumber(value) or 0
    elseif name == "vr" then vr_set, B738DR_fms_vr_set = value, tonumber(value) or 0
    else v2_set, B738DR_fms_v2_set = value, tonumber(value) or 0 end
end

local function get_speed(name)
    if name == "v1" then return v1_set elseif name == "vr" then return vr_set else return v2_set end
end

function fms.labels()
    local selected = SFP27DR_active == 1
    if ground_editable() then selected = core.supported(B738DR_b737_variant, B738DR_73x, B738DR_sfp) end
    if selected then
        engine_1k, engine_2k, engine_3k = "27K", "26K", "24K"
    elseif B738DR_b737_variant == 0 or (B738DR_b737_variant == -1 and B738DR_73x == 0) then
        engine_1k, engine_2k, engine_3k = "26K", "24K", "22K"
    end
end

local function validate_atm()
    local assumed = tonumber(sel_temp)
    local actual = tonumber(oat)
    if actual == nil and B738DR_aspirated_probe ~= 0 then actual = simDR_TAT end
    -- Allow ATM before a manual OAT entry; the producer publishes unavailable
    -- until that independent input is supplied. Never invent an OAT here.
    if assumed == nil or actual == nil then return end
    local rating = to == "<ACT>" and 27 or (to_1 == "<ACT>" and 26 or (to_2 == "<ACT>" and 24 or nil))
    local result = core.n1({rating = rating, altitude_ft = SFP27DR_altitude,
        oat_c = actual, assumed_c = assumed, packs_off_left = false, packs_off_right = false})
    if result == nil then
        -- Reject the entered ATM, preserving the selected fixed derate.
        -- Clearing the source prevents repeated messages and hidden clamping.
        sel_temp, sel_temp_f = "----", "----"
        add_fmc_msg(INVALID_INPUT, 0, 0)
        add_fmc_msg(INVALID_INPUT, 0, 1)
    end
end

function fms.sync()
    local previous = SFP27DR_active
    if ground_editable() then
        SFP27DR_active = core.supported(B738DR_b737_variant, B738DR_73x, B738DR_sfp) and 1 or 0
    end
    fms.labels()
    if not ground_editable() then return end
    if SFP27DR_active == 1 then validate_atm() end
    local key = "OFF"
    if SFP27DR_active == 1 then
        -- Raw FMC sources, before B738_calc republishes them as DataRefs.
        key = table.concat({tostring(B738DR_b737_variant), tostring(B738DR_73x),
            tostring(to), tostring(to_1), tostring(to_2), tostring(sel_temp), tostring(oat),
            tostring(gw_lbs), tostring(flaps), tostring(cg), tostring(rw_cond),
            tostring(ref_rwy), tostring(rw_wind_dir), tostring(rw_wind_spd),
            tostring(rw_slope), tostring(rw_hdg), string.format("%.0f", SFP27DR_altitude),
            tostring(SFP27DR_bleed1), tostring(SFP27DR_bleed2), tostring(SFP27DR_pack1),
            tostring(SFP27DR_pack2), tostring(SFP27DR_isolation),
            tostring(B738DR_aspirated_probe),
            B738DR_aspirated_probe ~= 0 and oat == "****" and string.format("%.1f", simDR_TAT) or "manual",
            tostring(ref_icao)}, "|")
    end
    if key ~= last_key or previous ~= SFP27DR_active then
        if previous == 1 or SFP27DR_active == 1 then
            -- Do not relabel a previous profile's numeric thrust as 27K while
            -- waiting for the next Calc publication. Keep original MAN/
            -- unavailable handling as the consumer of this zero sentinel.
            SFP27DR_n1_valid = 0
            for i = 0, 1 do
                B738DR_thr_takeoff_N1[i], B738DR_thr_takeoff_full_N1[i], SFP27DR_der_full[i] = 0, 0, 0
            end
            fmc_full_thrust, fmc_full_thrust2, fmc_dto_thrust, fmc_dto_thrust2 = 0, 0, 0, 0
            B738DR_fms_v1_calc, B738DR_fms_vr_calc, B738DR_fms_v2_calc = 0, 0, 0
            B738DR_trim_calc = 0
            for name, value in pairs(automatic) do
                if get_speed(name) == value then set_speed(name, "---") end
            end
            automatic = {}
            verify_to_spd = 0
        end
        SFP27DR_input_key = key
        last_key = key
    end
    if SFP27DR_active == 1 then
        local values = {v1 = B738DR_fms_v1_calc, vr = B738DR_fms_vr_calc, v2 = B738DR_fms_v2_calc}
        for name, value in pairs(automatic) do
            if get_speed(name) ~= value then
                automatic[name] = nil
            elseif tonumber(value) ~= values[name] then
                set_speed(name, "---")
                automatic[name] = nil
                verify_to_spd = 0
            end
        end
    end
end

function fms.accept_auto(name, value)
    -- Track original automatic acceptance even while SFP is off, so a later
    -- profile activation cannot retain old 26K values as independent manual input.
    fms.sync()
    if SFP27DR_active == 1 then
        local calculated = ({v1 = B738DR_fms_v1_calc, vr = B738DR_fms_vr_calc, v2 = B738DR_fms_v2_calc})[name]
        if SFP27DR_input_key ~= SFP27DR_calculated_key or calculated == nil or
           calculated <= 0 or tonumber(value) ~= calculated then
            set_speed(name, "---")
            return false
        end
    end
    automatic[name] = value
    return true
end

function fms.manual(name)
    automatic[name] = nil
end

function fms.reset()
    automatic, last_key = {}, nil
    SFP27DR_active, SFP27DR_n1_valid = 0, 0
    SFP27DR_input_key, SFP27DR_calculated_key = "", ""
end

raw_table("B738_sfp27_fms")
B738_sfp27_fms = fms
