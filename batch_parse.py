#!/usr/bin/env python3
"""F1 25 UDP 遥测数据解析器 —— 根据官方协议 + 实际大小校准"""

import struct
import json
import os
import glob

PACKET_DIR = "/Users/haha/f125/packets"
MAX_CARS = 22
WHEEL = ["RL", "RR", "FL", "FR"]

TEAMS = {
    0:"Mercedes", 1:"Ferrari", 2:"Red Bull Racing", 3:"Williams",
    4:"Aston Martin", 5:"Alpine", 6:"RB", 7:"Haas", 8:"McLaren", 9:"Sauber",
    41:"F1 Generic", 104:"F1 Custom Team",
}

EVENTS = {
    "SSTA":"Session Started","SEND":"Session Ended","FTLP":"Fastest Lap",
    "RTMT":"Retirement","DRSE":"DRS enabled","DRSD":"DRS disabled",
    "TMPT":"Team mate in pits","CHQF":"Chequered flag","RCWN":"Race Winner",
    "PENA":"Penalty Issued","SPTP":"Speed Trap Triggered","STLG":"Start lights",
    "LGOT":"Lights out","DTSV":"Drive through served","SGSV":"Stop go served",
    "FLBK":"Flashback","BUTN":"Button status","RDFL":"Red Flag",
    "OVTK":"Overtake","SCAR":"Safety Car","COLL":"Collision",
}

NAMES = {0:"Motion",1:"Session",2:"Lap Data",3:"Event",4:"Participants",
         5:"Car Setups",6:"Car Telemetry",7:"Car Status",8:"Final Classification",
         9:"Lobby Info",10:"Car Damage",11:"Session History",12:"Tyre Sets",
         13:"Motion Ex",14:"Time Trial",15:"Lap Positions"}

# ===== Format strings (verified against actual packet sizes) =====
F_HEADER        = "<HBBBBBQfIIBB"       # 29 bytes
F_MOTION        = "<ffffffhhhhhhffffff"  # 60 bytes: 6f + 6h + 6f
F_LAP           = "<"+"II"+"HB"*4+"fff"+"B"*14+"HH"+"B"+"f"+"H"  # 57 bytes
F_SETUP         = "<"+"B"*4+"f"*4+"B"*9+"f"*4+"B"+"f"  # 50 bytes
F_TELEMETRY     = "<"+"H"+"f"*3+"B"+"b"+"H"+"B"*2+"H"+"H"*4+"B"*4+"B"*4+"H"+"f"*4+"B"*4  # 60 bytes
F_STATUS        = "<"+"B"*5+"f"*3+"H"*2+"B"*2+"H"+"B"*2+"b"+"f"*3+"B"+"f"*3+"B"*2  # 55 bytes
F_DAMAGE        = "<"+"f"*4+"B"*12+"B"*18  # 46 bytes: 4f + 3*4B + 18B
F_MARSHAL       = "<fb"               # 5 bytes
F_WEATHER       = "<BBBbbbbB"         # 8 bytes (F1 25 spec)
F_LAP_HIST      = "<IHBHBHBB"         # 14 bytes
F_TYRE_STINT    = "<BBB"              # 3 bytes
F_TYRE_SET      = "<"+"B"*7+"h"+"B"  # 10 bytes
F_TIME_TRIAL    = "<BB IIII BBBB BB"  # 24 bytes
F_SESS_HIST_MAIN = "<BBBBBBB"         # 7 bytes


def parse_header(d):
    v = struct.unpack(F_HEADER, d[:29])
    return {"packet_format":v[0],"game_year":v[1],"game_major_ver":v[2],
            "game_minor_ver":v[3],"packet_version":v[4],"packet_id":v[5],
            "session_uid":v[6],"session_time":round(v[7],6),
            "frame_identifier":v[8],"overall_frame_id":v[9],
            "player_car_index":v[10],"secondary_player_car_index":v[11]}

def fval(x): return round(x, 4)

# ===== Packet decoders =====

def dec_motion(d):
    h = parse_header(d); off = 29; cars = []
    for i in range(MAX_CARS):
        v = struct.unpack(F_MOTION, d[off:off+60])
        cars.append({"car_index":i,
            "world_pos":{"x":fval(v[0]),"y":fval(v[1]),"z":fval(v[2])},
            "world_velocity":{"x":fval(v[3]),"y":fval(v[4]),"z":fval(v[5])},
            "forward_dir":{"x":v[6]/32767,"y":v[7]/32767,"z":v[8]/32767},
            "right_dir":{"x":v[9]/32767,"y":v[10]/32767,"z":v[11]/32767},
            "g_force":{"lateral":fval(v[12]),"longitudinal":fval(v[13]),"vertical":fval(v[14])},
            "yaw":fval(v[15]),"pitch":fval(v[16]),"roll":fval(v[17])})
        off += 60
    return {"header":h, "car_motion_data":cars}

def dec_session(d):
    h = parse_header(d); off = 29
    # Skip tag (4 bytes) — already part of the 29-byte header in our scheme
    # Actually the tag at offset 29 is part of the body, not the header
    off += 4  # skip tag bytes

    # First block: weather + session info (18 bytes)
    v = struct.unpack("<bb B H B b B B H H B B B B B", d[off:off+18]); off += 18

    # Marshal zones (21 × 5 bytes)
    marshal = []
    for _ in range(21):
        m = struct.unpack(F_MARSHAL, d[off:off+5])
        marshal.append({"zone_start":fval(m[0]),"zone_flag":m[1]}); off += 5

    # Second block: safety car + weather count (3 bytes)
    v2 = struct.unpack("<BBB", d[off:off+3]); off += 3

    # Weather forecast (64 × 8 bytes)
    weather = []
    for _ in range(64):
        w = struct.unpack(F_WEATHER, d[off:off+8])
        weather.append({"session_type":w[0],"time_offset":w[1],"weather":w[2],
            "track_temperature":w[3],"track_temp_change":w[4],
            "air_temperature":w[5],"air_temp_change":w[6],"rain_percentage":w[7]})
        off += 8

    # Reserved block (16 bytes) — all zeros in practice
    off += 16

    # Mid block: forecast accuracy, AI, link IDs, assists (32 bytes)
    mid = struct.unpack("<"+"B"*2+"III"+"B"*18, d[off:off+32]); off += 32

    # End block: game settings (26 bytes: I + 22*B)
    end = struct.unpack("<I"+"B"*22, d[off:off+26]); off += 26

    # Last block: sector distances (8 bytes: 2 floats)
    last = struct.unpack("<ff", d[off:off+8]); off += 8

    return {"header":h,
        "weather":v[0],"track_temperature":v[1],"air_temperature":v[2],
        "total_laps":v[3],"track_length":v[4],"session_type":v[5],"track_id":v[6],
        "formula":v[7],"session_time_left":v[8],"session_duration":v[9],
        "pit_speed_limit":v[10],"game_paused":v[11],"is_spectating":v[12],
        "spectator_car_index":v[13],"sli_pro_native_support":v[14],
        "marshal_zones":marshal,
        "safety_car_status":v2[0],"network_game":v2[1],
        "num_weather_forecast_samples":v2[2],
        "weather_forecast_samples":weather,
        "forecast_accuracy":mid[0],"ai_difficulty":mid[1],
        "season_link_id":mid[2],"weekend_link_id":mid[3],"session_link_id":mid[4],
        "pit_stop_window_ideal_lap":mid[5],"pit_stop_window_latest_lap":mid[6],
        "pit_stop_rejoin_position":mid[7],"steering_assist":mid[8],
        "braking_assist":mid[9],"gearbox_assist":mid[10],"pit_assist":mid[11],
        "pit_release_assist":mid[12],"ers_assist":mid[13],"drs_assist":mid[14],
        "dynamic_racing_line":mid[15],"dynamic_racing_line_type":mid[16],
        "settings":{
            "game_mode":end[0],"rule_set":end[1],"time_of_day":end[2],
            "session_length":end[3],"speed_units_lead":end[4],"temp_units_lead":end[5],
            "speed_units_secondary":end[6],"temp_units_secondary":end[7],
            "num_safety_car_periods":end[8],"num_vsc_periods":end[9],
            "num_red_flag_periods":end[10],"equal_car_performance":end[11],
            "recovery_mode":end[12],"flashback_limit":end[13],"surface_type":end[14],
            "low_fuel_mode":end[15],"race_starts":end[16],"tyre_temperature":end[17],
            "pit_lane_tyre_sim":end[18],"car_damage":end[19],"car_damage_rate":end[20],
            "collisions":end[21],"collisions_off_first_lap_only":end[22]},
        "sector2_lap_distance_start":fval(last[0]),
        "sector3_lap_distance_start":fval(last[1])}

def dec_lap(d):
    h = parse_header(d); off = 29; cars = []
    for i in range(MAX_CARS):
        v = struct.unpack(F_LAP, d[off:off+57])
        cars.append({"car_index":i,
            "last_lap_time_ms":v[0],"current_lap_time_ms":v[1],
            "sector1_time_ms":v[2]+v[3]*60000,"sector2_time_ms":v[4]+v[5]*60000,
            "delta_to_car_in_front_ms":v[6]+v[7]*60000,"delta_to_race_leader_ms":v[8]+v[9]*60000,
            "lap_distance":fval(v[10]),"total_distance":fval(v[11]),"safety_car_delta":fval(v[12]),
            "car_position":v[13],"current_lap_num":v[14],"pit_status":v[15],
            "num_pit_stops":v[16],"sector":v[17],"current_lap_invalid":v[18],
            "penalties":v[19],"total_warnings":v[20],"corner_cutting_warnings":v[21],
            "num_unserved_drive_through":v[22],"num_unserved_stop_go":v[23],
            "grid_position":v[24],"driver_status":v[25],"result_status":v[26],
            "pit_lane_timer_active":v[27],"pit_lane_time_in_lane_ms":v[28],
            "pit_stop_timer_ms":v[29],"pit_stop_should_serve_pen":v[30],
            "speed_trap_fastest_speed":fval(v[31])})
        off += 57
    xtra = struct.unpack("<BB", d[off:off+2])
    return {"header":h, "lap_data":cars,
            "time_trial_pb_car_idx":xtra[0],"time_trial_rival_car_idx":xtra[1]}

def dec_event(d):
    h = parse_header(d)
    code = d[29:33].decode("ascii","replace").rstrip("\x00")
    name = EVENTS.get(code,"Unknown")
    p = d[33:]; det = {"event":name}
    if code=="BUTN":
        bt = struct.unpack("<I",p[:4])[0]
        det.update({"button_status_raw":bt,"buttons_pressed":[i for i in range(32) if (bt>>i)&1]})
    elif code=="FTLP":
        v=struct.unpack("<Bf",p[:5]); det.update({"vehicle_idx":v[0],"lap_time":fval(v[1])})
    elif code=="RTMT":
        det.update({"vehicle_idx":p[0],"retirement_reason":p[1] if len(p)>1 else None})
    elif code=="SPTP":
        v=struct.unpack("<BfBBBf",p[:12])
        det.update({"vehicle_idx":v[0],"speed":fval(v[1]),"is_overall_fastest":v[2],
            "is_driver_fastest":v[3],"fastest_vehicle_idx":v[4],"fastest_speed":fval(v[5])})
    elif code=="STLG": det["num_lights"]=p[0]
    elif code=="FLBK":
        v=struct.unpack("<If",p[:8]); det.update({"flashback_frame_id":v[0],"flashback_session_time":fval(v[1])})
    elif code=="SGSV":
        v=struct.unpack("<Bf",p[:5]); det.update({"vehicle_idx":v[0],"stop_time":fval(v[1])})
    elif code in ("OVTK","COLL"):
        det.update({"vehicle1_idx":p[0],"vehicle2_idx":p[1]})
    elif code=="SCAR":
        det.update({"safety_car_type":p[0],"event_type":p[1]})
    elif code in ("DTSV","RCWN","TMPT"):
        det["vehicle_idx"]=p[0]
    elif code=="PENA":
        det["raw_hex"]=p[:7].hex()
    else:
        det["raw_hex"]=p.hex()
    return {"header":h,"event_code":code,"details":det}

def dec_participants(d):
    h = parse_header(d); off = 29
    num = d[off]; off += 1; parts = []
    for i in range(MAX_CARS):
        name_raw = d[off:off+32]
        npos = name_raw.find(b'\x00')
        name = name_raw[:npos].decode("utf-8","replace") if npos>=0 else name_raw.decode("utf-8","replace")
        v = struct.unpack("<BBBBBBB B B H B B", d[off+32:off+45])
        ncol = v[9]; cols = []
        for c in range(4):
            if c < ncol:
                rgb = d[off+45+c*3:off+48+c*3]
                if len(rgb)==3: cols.append({"r":rgb[0],"g":rgb[1],"b":rgb[2]})
        parts.append({"car_index":i,"ai_controlled":v[0],"driver_id":v[1],"network_id":v[2],
            "team_id":v[3],"team_name":TEAMS.get(v[3],f"Unknown({v[3]})"),
            "my_team":v[4],"race_number":v[5],"nationality":v[6],"name":name,
            "your_telemetry":v[7],"show_online_names":v[8],"tech_level":v[9],
            "platform":v[10],"livery_colours":cols})
        off += 45 + 12
    return {"header":h,"num_active_cars":num,"participants":parts}

def dec_setups(d):
    h = parse_header(d); off = 29; cars = []
    for i in range(MAX_CARS):
        v = struct.unpack(F_SETUP, d[off:off+50])
        cars.append({"car_index":i,
            "front_wing":v[0],"rear_wing":v[1],"on_throttle_diff":v[2],"off_throttle_diff":v[3],
            "front_camber":fval(v[4]),"rear_camber":fval(v[5]),"front_toe":fval(v[6]),"rear_toe":fval(v[7]),
            "front_suspension":v[8],"rear_suspension":v[9],
            "front_anti_roll_bar":v[10],"rear_anti_roll_bar":v[11],
            "front_suspension_height":v[12],"rear_suspension_height":v[13],
            "brake_pressure":v[14],"brake_bias":v[15],"engine_braking":v[16],
            "rear_left_tyre_pressure":fval(v[17]),"rear_right_tyre_pressure":fval(v[18]),
            "front_left_tyre_pressure":fval(v[19]),"front_right_tyre_pressure":fval(v[20]),
            "ballast":v[21],"fuel_load":fval(v[22])})
        off += 50
    nw = struct.unpack("<f",d[off:off+4])[0]
    return {"header":h,"car_setups":cars,"next_front_wing_value":fval(nw)}

def dec_telemetry(d):
    h = parse_header(d); off = 29; cars = []
    for i in range(MAX_CARS):
        v = struct.unpack(F_TELEMETRY, d[off:off+60])
        cars.append({"car_index":i,
            "speed":v[0],"throttle":fval(v[1]),"steer":fval(v[2]),"brake":fval(v[3]),
            "clutch":v[4],"gear":v[5],"engine_rpm":v[6],"drs":v[7],
            "rev_lights_percent":v[8],"rev_lights_bit_value":v[9],
            "brakes_temperature":{WHEEL[j]:v[10+j] for j in range(4)},
            "tyres_surface_temperature":{WHEEL[j]:v[14+j] for j in range(4)},
            "tyres_inner_temperature":{WHEEL[j]:v[18+j] for j in range(4)},
            "engine_temperature":v[22],
            "tyres_pressure":{WHEEL[j]:fval(v[23+j]) for j in range(4)},
            "surface_type":{WHEEL[j]:v[27+j] for j in range(4)}})
        off += 60
    xtra = struct.unpack("<BBb",d[off:off+3])
    return {"header":h,"car_telemetry_data":cars,
            "mfd_panel_index":xtra[0],"mfd_panel_index_secondary":xtra[1],"suggested_gear":xtra[2]}

def dec_status(d):
    h = parse_header(d); off = 29; cars = []
    for i in range(MAX_CARS):
        v = struct.unpack(F_STATUS, d[off:off+55])
        cars.append({"car_index":i,
            "traction_control":v[0],"anti_lock_brakes":v[1],"fuel_mix":v[2],
            "front_brake_bias":v[3],"pit_limiter_status":v[4],
            "fuel_in_tank":fval(v[5]),"fuel_capacity":fval(v[6]),"fuel_remaining_laps":fval(v[7]),
            "max_rpm":v[8],"idle_rpm":v[9],"max_gears":v[10],"drs_allowed":v[11],
            "drs_activation_distance":v[12],"actual_tyre_compound":v[13],"visual_tyre_compound":v[14],
            "tyres_age_laps":v[15],"vehicle_fia_flags":v[16],
            "engine_power_ice":fval(v[17]),"engine_power_mguk":fval(v[18]),
            "ers_store_energy":fval(v[19]),"ers_deploy_mode":v[20],
            "ers_harvested_this_lap_mguk":fval(v[21]),"ers_harvested_this_lap_mguh":fval(v[22]),
            "ers_deployed_this_lap":fval(v[23]),"network_paused":v[24]})
        off += 55
    return {"header":h,"car_status_data":cars}

def dec_damage(d):
    h = parse_header(d); off = 29; cars = []
    for i in range(MAX_CARS):
        v = struct.unpack(F_DAMAGE, d[off:off+46])
        cars.append({"car_index":i,
            "tyres_wear":{WHEEL[j]:fval(v[j]) for j in range(4)},
            "tyres_damage":{WHEEL[j]:v[4+j] for j in range(4)},
            "brakes_damage":{WHEEL[j]:v[8+j] for j in range(4)},
            "tyre_blisters":{WHEEL[j]:v[12+j] for j in range(4)},
            "front_left_wing_damage":v[16],"front_right_wing_damage":v[17],
            "rear_wing_damage":v[18],"floor_damage":v[19],"diffuser_damage":v[20],
            "sidepod_damage":v[21],"drs_fault":v[22],"ers_fault":v[23],
            "gear_box_damage":v[24],"engine_damage":v[25],"engine_mguh_wear":v[26],
            "engine_es_wear":v[27],"engine_ce_wear":v[28],"engine_ice_wear":v[29],
            "engine_mguk_wear":v[30],"engine_tc_wear":v[31],
            "engine_blown":v[32],"engine_seized":v[33]})
        off += 46
    return {"header":h,"car_damage_data":cars}

def dec_session_history(d):
    h = parse_header(d); off = 29
    v = struct.unpack(F_SESS_HIST_MAIN, d[off:off+7]); off += 7
    car_idx, n_laps, n_stints = v[0], v[1], v[2]

    laps = []
    for _ in range(100):
        l = struct.unpack(F_LAP_HIST, d[off:off+14])
        laps.append({"lap_time_ms":l[0],"sector1_time_ms":l[1]+l[2]*60000,
            "sector2_time_ms":l[3]+l[4]*60000,"sector3_time_ms":l[5]+l[6]*60000,
            "lap_valid_bit_flags":l[7]})
        off += 14

    stints = []
    for _ in range(8):
        s = struct.unpack(F_TYRE_STINT, d[off:off+3])
        stints.append({"end_lap":s[0],"tyre_actual_compound":s[1],"tyre_visual_compound":s[2]})
        off += 3

    return {"header":h,"car_idx":car_idx,"num_laps":n_laps,"num_tyre_stints":n_stints,
        "best_lap_time_lap_num":v[3],"best_sector1_lap_num":v[4],
        "best_sector2_lap_num":v[5],"best_sector3_lap_num":v[6],
        "lap_history_data":laps[:n_laps],"tyre_stints_history_data":stints[:n_stints]}

def dec_tyre_sets(d):
    h = parse_header(d); off = 29
    car_idx = d[off]; off += 1
    sets = []
    for _ in range(20):
        t = struct.unpack(F_TYRE_SET, d[off:off+10])
        sets.append({"actual_tyre_compound":t[0],"visual_tyre_compound":t[1],"wear":t[2],
            "available":t[3],"recommended_session":t[4],"life_span":t[5],"usable_life":t[6],
            "lap_delta_time":t[7],"fitted":t[8]})
        off += 10
    fitted = d[off]
    return {"header":h,"car_idx":car_idx,"tyre_set_data":sets,"fitted_idx":fitted}

def dec_motion_ex(d):
    h = parse_header(d); off = 29
    def rf(n):
        nonlocal off
        v = struct.unpack(f"<{n}f", d[off:off+n*4]); off += n*4
        return [round(x,6) for x in v]
    r = {"header":h}
    r["suspension_position"]={WHEEL[i]:v for i,v in enumerate(rf(4))}
    r["suspension_velocity"]={WHEEL[i]:v for i,v in enumerate(rf(4))}
    r["suspension_acceleration"]={WHEEL[i]:v for i,v in enumerate(rf(4))}
    r["wheel_speed"]={WHEEL[i]:v for i,v in enumerate(rf(4))}
    r["wheel_slip_ratio"]={WHEEL[i]:v for i,v in enumerate(rf(4))}
    r["wheel_slip_angle"]={WHEEL[i]:v for i,v in enumerate(rf(4))}
    r["wheel_lat_force"]={WHEEL[i]:v for i,v in enumerate(rf(4))}
    r["wheel_long_force"]={WHEEL[i]:v for i,v in enumerate(rf(4))}
    r["height_of_cog_above_ground"]=rf(1)[0]
    r["local_velocity"]={"x":rf(1)[0],"y":rf(1)[0],"z":rf(1)[0]}
    r["angular_velocity"]={"x":rf(1)[0],"y":rf(1)[0],"z":rf(1)[0]}
    r["angular_acceleration"]={"x":rf(1)[0],"y":rf(1)[0],"z":rf(1)[0]}
    r["front_wheels_angle"]=rf(1)[0]
    r["wheel_vert_force"]={WHEEL[i]:v for i,v in enumerate(rf(4))}
    r["front_aero_height"]=rf(1)[0]; r["rear_aero_height"]=rf(1)[0]
    r["front_roll_angle"]=rf(1)[0]; r["rear_roll_angle"]=rf(1)[0]
    r["chassis_yaw"]=rf(1)[0]; r["chassis_pitch"]=rf(1)[0]
    r["wheel_camber"]={WHEEL[i]:v for i,v in enumerate(rf(4))}
    r["wheel_camber_gain"]={WHEEL[i]:v for i,v in enumerate(rf(4))}
    return r

def dec_time_trial(d):
    h = parse_header(d); off = 29
    sets = []
    for _ in range(3):
        v = struct.unpack(F_TIME_TRIAL, d[off:off+24])
        sets.append({"car_idx":v[0],"team_id":v[1],"team_name":TEAMS.get(v[1],f"Unknown({v[1]})"),
            "lap_time_ms":v[2],"sector1_time_ms":v[3],"sector2_time_ms":v[4],"sector3_time_ms":v[5],
            "traction_control":v[6],"gearbox_assist":v[7],"anti_lock_brakes":v[8],
            "equal_car_performance":v[9],"custom_setup":v[10],"valid":v[11]})
        off += 24
    return {"header":h,"player_session_best":sets[0],"personal_best":sets[1],"rival":sets[2]}

def dec_lap_positions(d):
    h = parse_header(d); off = 29
    n_laps = d[off]; off += 1
    lap_start = d[off]; off += 1
    pos = []
    for lap in range(min(n_laps, 50)):
        pos.append({"lap":lap_start+lap,"positions":list(d[off:off+MAX_CARS])})
        off += MAX_CARS
    return {"header":h,"num_laps":n_laps,"lap_start":lap_start,"lap_positions":pos}

DECODERS = {0:dec_motion,1:dec_session,2:dec_lap,3:dec_event,4:dec_participants,
            5:dec_setups,6:dec_telemetry,7:dec_status,10:dec_damage,
            11:dec_session_history,12:dec_tyre_sets,13:dec_motion_ex,
            14:dec_time_trial,15:dec_lap_positions}

def parse_packet(data, filename):
    if len(data) < 29: return {"filename":filename,"error":"too short"}
    pkt_id = data[6]
    name = NAMES.get(pkt_id, f"Unknown({pkt_id})")
    decoder = DECODERS.get(pkt_id)
    try:
        result = decoder(data) if decoder else {"header":parse_header(data),"_payload_hex":data[29:].hex()[:200]}
    except Exception as e:
        result = {"header":parse_header(data),"_error":str(e),"_payload_hex":data[29:].hex()[:200]}
    result["packet_name"] = name
    result["filename"] = filename
    try:
        parts = filename.replace(".bin","").split("_")
        result["timestamp_us"] = int(parts[0])
        result["source_port"] = int(parts[1])
    except: pass
    return result

def main():
    files = sorted(glob.glob(f"{PACKET_DIR}/*.bin"))
    if not files: print(f"No .bin files in {PACKET_DIR}"); return
    print(f"Parsing {len(files)} packet files...")
    out_path = os.path.join(os.path.dirname(PACKET_DIR), "parsed_packets.ndjson")
    from collections import Counter
    tcnt = Counter(); errs = 0
    with open(out_path,"w") as out:
        for i, fp in enumerate(files):
            fn = os.path.basename(fp)
            with open(fp,"rb") as f: data = f.read()
            rec = parse_packet(data, fn)
            out.write(json.dumps(rec, ensure_ascii=False)+"\n")
            tcnt[data[6]] += 1
            if "_error" in rec: errs += 1
            if (i+1)%10000==0: print(f"  {i+1}/{len(files)}")
    print(f"\nDone. {len(files)} packets → {out_path}")
    if errs: print(f"  Errors: {errs}")
    else: print(f"  All clean — 0 errors!")
    print("\n=== 包类型 ===")
    for t in sorted(tcnt):
        print(f"  ID {t:>2}: {NAMES.get(t,'?'):<25} × {tcnt[t]}")
    if errs:
        print("\n=== 错误样例 ===")
        with open(out_path) as f:
            for line in f:
                obj = json.loads(line)
                if "_error" in obj:
                    print(json.dumps(obj, ensure_ascii=False, indent=2)[:600])
                    break
    else:
        print("\n=== 样例 ===")
        seen = {}
        with open(out_path) as f:
            for line in f:
                obj = json.loads(line)
                t = obj["header"]["packet_id"]
                if t not in seen: seen[t] = obj
        for t in sorted(seen):
            obj = seen[t]
            print(f"\n--- ID {t}: {obj['packet_name']} (session_time={obj['header']['session_time']}) ---")
            d = json.dumps(obj, ensure_ascii=False, indent=2)
            print(d[:1200] + ("..." if len(d)>1200 else ""))

if __name__ == "__main__":
    main()
