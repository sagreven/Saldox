#!/usr/bin/with-contenv bashio
# Saldox EMS Bridge — entrypoint. Leest add-on opties via bashio, exporteert
# ze als env-vars en start de Python-app.
set -e

bashio::log.info "Saldox EMS Bridge starting…"

export MODBUS_CONNECTION_TYPE="$(bashio::config 'modbus.connection_type' 'tcp')"
export MODBUS_HOST="$(bashio::config 'modbus.host' '192.168.1.50')"
export MODBUS_PORT="$(bashio::config 'modbus.port' 502)"
export MODBUS_SERIAL_PORT="$(bashio::config 'modbus.serial_port' '/dev/ttyUSB0')"
export MODBUS_BAUDRATE="$(bashio::config 'modbus.baudrate' 9600)"
export MODBUS_PARITY="$(bashio::config 'modbus.parity' 'N')"
export MODBUS_STOPBITS="$(bashio::config 'modbus.stopbits' 1)"
export MODBUS_UNIT_ID="$(bashio::config 'modbus.unit_id' 1)"
export POLL_INTERVAL="$(bashio::config 'modbus.poll_interval_seconds' 10)"

export HA_DEVICE_SLUG="$(bashio::config 'ha.device_slug' 'sofar_hyd')"
export HA_FRIENDLY_NAME="$(bashio::config 'ha.friendly_name' 'Sofar HYD')"

export PRICES_SLUG="$(bashio::config 'prices.slug' 'saldox_price')"
export PRICES_POLL_MINUTES="$(bashio::config 'prices.poll_minutes' 15)"

export SALDOX_API_URL="$(bashio::config 'saldox_api_url' '')"
export SALDOX_API_TOKEN="$(bashio::config 'saldox_api_token' '')"

# Supervisor levert deze automatisch zodat we naar de HA core API kunnen schrijven.
# SUPERVISOR_TOKEN is gezet wanneer hassio_api: true / homeassistant_api: true.
export HA_SUPERVISOR_URL="http://supervisor/core"
# SUPERVISOR_TOKEN al gezet door de runtime — alleen doorlinken voor duidelijkheid.

if [ "${MODBUS_CONNECTION_TYPE}" = "serial" ]; then
  bashio::log.info "Serial RTU via ${MODBUS_SERIAL_PORT} @ ${MODBUS_BAUDRATE} 8${MODBUS_PARITY}${MODBUS_STOPBITS} (unit ${MODBUS_UNIT_ID}) iedere ${POLL_INTERVAL}s"
else
  bashio::log.info "Polling ${MODBUS_HOST}:${MODBUS_PORT} (unit ${MODBUS_UNIT_ID}) iedere ${POLL_INTERVAL}s"
fi
bashio::log.info "Publishing inverter naar sensor.${HA_DEVICE_SLUG}_* in Home Assistant"
if [ -n "${SALDOX_API_URL}" ]; then
  bashio::log.info "Saldox prices via ${SALDOX_API_URL}: sensor.${PRICES_SLUG}_* (iedere ${PRICES_POLL_MINUTES} min)"
fi

cd /app
exec python3 -m saldox_addon.main
