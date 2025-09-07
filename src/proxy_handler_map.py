from process_proxy.mobbin import handlers as mobbin_handlers
from process_proxy.refero import handlers as refero_handlers
from process_proxy.uxmovement import handlers as uxmovement_handlers
from process_proxy.iconly import handlers as iconly_handlers
from process_proxy.craftwork import handlers as craftwork_handlers
from process_proxy.flaticon import handlers as flaticon_handlers
from process_proxy.freepik import handlers as freepik_handlers
from process_proxy.envato import handlers as envato_handlers

proxy_handler_map = {
    "mobbin": mobbin_handlers,
    "uxmovement": uxmovement_handlers,
    "refero": refero_handlers,
    "iconly": iconly_handlers,
    "craftwork": craftwork_handlers,
    "flaticon": flaticon_handlers,
    "freepik": freepik_handlers,
    "envato": envato_handlers,
}