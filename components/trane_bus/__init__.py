from esphome import automation
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import canbus
from esphome.const import CONF_ID

CODEOWNERS = []
DEPENDENCIES = ["canbus"]

CONF_CANBUS_ID = "canbus_id"
CONF_COMMAND_CAN_ID = "command_can_id"
CONF_TX_ENABLED = "tx_enabled"
CONF_RAW_JSON_ENABLED = "raw_json_enabled"
CONF_REQUIRE_SC360_BEFORE_TX = "require_sc360_before_tx"
CONF_BUS_ACTIVITY_TIMEOUT = "bus_activity_timeout"
CONF_ACK_TIMEOUT = "ack_timeout"
CONF_SETPOINT_MIN_F = "setpoint_min_f"
CONF_SETPOINT_MAX_F = "setpoint_max_f"
CONF_MIN_DEADBAND_F = "min_deadband_f"
CONF_CAPTURE_CAPACITY = "capture_capacity"
CONF_CAPTURE_ENABLED = "capture_enabled"
CONF_ON_JSON = "on_json"
CONF_PAYLOAD = "payload"
CONF_ENABLED = "enabled"
CONF_MODE = "mode"
CONF_HEAT_F = "heat_f"
CONF_COOL_F = "cool_f"
CONF_ZONE = "zone"
CONF_HOLD_TYPE = "hold_type"
CONF_SOURCE = "source"
CONF_PROFILE = "profile"

trane_bus_ns = cg.esphome_ns.namespace("trane_bus")
TraneBus = trane_bus_ns.class_("TraneBus", cg.Component)
TraneBusSendJsonAction = trane_bus_ns.class_("TraneBusSendJsonAction", automation.Action)
TraneBusSetTxEnabledAction = trane_bus_ns.class_("TraneBusSetTxEnabledAction", automation.Action)
TraneBusSetModeAction = trane_bus_ns.class_("TraneBusSetModeAction", automation.Action)
TraneBusSetSetpointsAction = trane_bus_ns.class_("TraneBusSetSetpointsAction", automation.Action)
TraneBusGetProfileAction = trane_bus_ns.class_("TraneBusGetProfileAction", automation.Action)

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(TraneBus),
        cv.Required(CONF_CANBUS_ID): cv.use_id(canbus.CanbusComponent),
        cv.Optional(CONF_COMMAND_CAN_ID, default=0x641): cv.int_range(min=0, max=0x7FF),
        cv.Optional(CONF_TX_ENABLED, default=False): cv.boolean,
        cv.Optional(CONF_RAW_JSON_ENABLED, default=False): cv.boolean,
        cv.Optional(CONF_REQUIRE_SC360_BEFORE_TX, default=True): cv.boolean,
        cv.Optional(CONF_BUS_ACTIVITY_TIMEOUT, default="5min"): cv.positive_time_period_milliseconds,
        cv.Optional(CONF_ACK_TIMEOUT, default="3s"): cv.positive_time_period_milliseconds,
        cv.Optional(CONF_SETPOINT_MIN_F, default=50.0): cv.float_range(min=40, max=80),
        cv.Optional(CONF_SETPOINT_MAX_F, default=90.0): cv.float_range(min=70, max=100),
        cv.Optional(CONF_MIN_DEADBAND_F, default=2.0): cv.float_range(min=1, max=10),
        cv.Optional(CONF_CAPTURE_CAPACITY, default=0): cv.int_range(min=0, max=16384),
        cv.Optional(CONF_CAPTURE_ENABLED, default=False): cv.boolean,
        cv.Optional(CONF_ON_JSON): automation.validate_automation(single=True),
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    can = await cg.get_variable(config[CONF_CANBUS_ID])
    cg.add(var.set_canbus(can))
    cg.add(var.set_command_can_id(config[CONF_COMMAND_CAN_ID]))
    cg.add(var.set_tx_enabled(config[CONF_TX_ENABLED]))
    cg.add(var.set_raw_json_enabled(config[CONF_RAW_JSON_ENABLED]))
    cg.add(var.set_require_sc360_before_tx(config[CONF_REQUIRE_SC360_BEFORE_TX]))
    cg.add(var.set_bus_activity_timeout_ms(config[CONF_BUS_ACTIVITY_TIMEOUT].total_milliseconds))
    cg.add(var.set_ack_timeout_ms(config[CONF_ACK_TIMEOUT].total_milliseconds))
    cg.add(var.set_setpoint_min_f(config[CONF_SETPOINT_MIN_F]))
    cg.add(var.set_setpoint_max_f(config[CONF_SETPOINT_MAX_F]))
    cg.add(var.set_min_deadband_f(config[CONF_MIN_DEADBAND_F]))
    cg.add(var.set_capture_capacity(config[CONF_CAPTURE_CAPACITY]))
    cg.add(var.set_capture_enabled(config[CONF_CAPTURE_ENABLED]))

    if CONF_ON_JSON in config:
        await automation.build_automation(
            var.get_json_trigger(),
            [(cg.std_string, "json"), (cg.uint32, "can_id")],
            config[CONF_ON_JSON],
        )


@automation.register_action(
    "trane_bus.send_json",
    TraneBusSendJsonAction,
    cv.Schema({cv.GenerateID(CONF_ID): cv.use_id(TraneBus), cv.Required(CONF_PAYLOAD): cv.templatable(cv.string_strict)}),
    synchronous=True,
)
async def send_json_action_to_code(config, action_id, template_arg, args):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    cg.add(var.set_payload(await cg.templatable(config[CONF_PAYLOAD], args, cg.std_string)))
    return var


@automation.register_action(
    "trane_bus.set_tx_enabled",
    TraneBusSetTxEnabledAction,
    cv.Schema({cv.GenerateID(CONF_ID): cv.use_id(TraneBus), cv.Required(CONF_ENABLED): cv.templatable(cv.boolean)}),
    synchronous=True,
)
async def set_tx_enabled_action_to_code(config, action_id, template_arg, args):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    cg.add(var.set_enabled(await cg.templatable(config[CONF_ENABLED], args, cg.bool_)))
    return var


@automation.register_action(
    "trane_bus.set_mode",
    TraneBusSetModeAction,
    cv.Schema({cv.GenerateID(CONF_ID): cv.use_id(TraneBus), cv.Required(CONF_MODE): cv.templatable(cv.string_strict)}),
    synchronous=True,
)
async def set_mode_action_to_code(config, action_id, template_arg, args):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    cg.add(var.set_mode(await cg.templatable(config[CONF_MODE], args, cg.std_string)))
    return var


@automation.register_action(
    "trane_bus.set_setpoints",
    TraneBusSetSetpointsAction,
    cv.Schema(
        {
            cv.GenerateID(CONF_ID): cv.use_id(TraneBus),
            cv.Required(CONF_HEAT_F): cv.templatable(cv.float_),
            cv.Required(CONF_COOL_F): cv.templatable(cv.float_),
            cv.Optional(CONF_ZONE, default=1): cv.templatable(cv.int_range(min=1, max=6)),
            cv.Optional(CONF_HOLD_TYPE, default=2): cv.templatable(cv.int_range(min=0, max=2)),
            cv.Optional(CONF_SOURCE, default=1): cv.templatable(cv.int_range(min=0, max=2)),
        }
    ),
    synchronous=True,
)
async def set_setpoints_action_to_code(config, action_id, template_arg, args):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    cg.add(var.set_heat_f(await cg.templatable(config[CONF_HEAT_F], args, cg.float_)))
    cg.add(var.set_cool_f(await cg.templatable(config[CONF_COOL_F], args, cg.float_)))
    cg.add(var.set_zone(await cg.templatable(config[CONF_ZONE], args, cg.int_)))
    cg.add(var.set_hold_type(await cg.templatable(config[CONF_HOLD_TYPE], args, cg.int_)))
    cg.add(var.set_source(await cg.templatable(config[CONF_SOURCE], args, cg.int_)))
    return var


@automation.register_action(
    "trane_bus.get_profile",
    TraneBusGetProfileAction,
    cv.Schema({cv.GenerateID(CONF_ID): cv.use_id(TraneBus), cv.Required(CONF_PROFILE): cv.templatable(cv.string_strict)}),
    synchronous=True,
)
async def get_profile_action_to_code(config, action_id, template_arg, args):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    cg.add(var.set_profile(await cg.templatable(config[CONF_PROFILE], args, cg.std_string)))
    return var
