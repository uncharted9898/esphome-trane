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
CONF_PAYLOAD = "payload"
CONF_ENABLED = "enabled"

trane_bus_ns = cg.esphome_ns.namespace("trane_bus")
TraneBus = trane_bus_ns.class_("TraneBus", cg.Component)
TraneBusSendJsonAction = trane_bus_ns.class_(
    "TraneBusSendJsonAction", automation.Action
)
TraneBusSetTxEnabledAction = trane_bus_ns.class_(
    "TraneBusSetTxEnabledAction", automation.Action
)

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(TraneBus),
        cv.Required(CONF_CANBUS_ID): cv.use_id(canbus.CanbusComponent),
        cv.Optional(CONF_COMMAND_CAN_ID, default=0x641): cv.int_range(
            min=0, max=0x7FF
        ),
        # Safe startup default: monitor-only until deliberately enabled.
        cv.Optional(CONF_TX_ENABLED, default=False): cv.boolean,
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    can = await cg.get_variable(config[CONF_CANBUS_ID])
    cg.add(var.set_canbus(can))
    cg.add(var.set_command_can_id(config[CONF_COMMAND_CAN_ID]))
    cg.add(var.set_tx_enabled(config[CONF_TX_ENABLED]))


SEND_JSON_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_ID): cv.use_id(TraneBus),
        cv.Required(CONF_PAYLOAD): cv.templatable(cv.string_strict),
    }
)


@automation.register_action(
    "trane_bus.send_json",
    TraneBusSendJsonAction,
    SEND_JSON_SCHEMA,
    synchronous=True,
)
async def send_json_action_to_code(config, action_id, template_arg, args):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    payload = await cg.templatable(config[CONF_PAYLOAD], args, cg.std_string)
    cg.add(var.set_payload(payload))
    return var


SET_TX_ENABLED_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_ID): cv.use_id(TraneBus),
        cv.Required(CONF_ENABLED): cv.templatable(cv.boolean),
    }
)


@automation.register_action(
    "trane_bus.set_tx_enabled",
    TraneBusSetTxEnabledAction,
    SET_TX_ENABLED_SCHEMA,
    synchronous=True,
)
async def set_tx_enabled_action_to_code(config, action_id, template_arg, args):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    enabled = await cg.templatable(config[CONF_ENABLED], args, cg.bool_)
    cg.add(var.set_enabled(enabled))
    return var
