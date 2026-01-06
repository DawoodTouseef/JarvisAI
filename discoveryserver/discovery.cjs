const express = require('express');
const cors = require('cors');
const bonjour = require('bonjour')();

const app = express();
app.use(cors());

const PORT = process.env.PORT || 3001;
// By default do not filter services server-side so we show all discovered services in the UI.
// You may set SERVICE_NAME env var to enable a default filter (e.g. SERVICE_NAME=J.A.R.V.I.S.)
const SERVICE_NAME_FILTER = process.env.SERVICE_NAME || '';

const services = new Map();

console.log('Discovery initialized. Service name filter:', SERVICE_NAME_FILTER || '<none>');

function serviceId(s) {
  return `${s.fqdn || s.host || s.name}:${s.port || ''}`;
}

const browser = bonjour.find({});

browser.on('up', (service) => {
  if (!service) {
    console.warn('Bonjour emitted "up" with undefined service');
    return;
  }
  const id = serviceId(service);
  services.set(id, {
    id,
    name: service.name || '<unknown>',
    fqdn: service.fqdn,
    host: service.host,
    port: service.port,
    addresses: service.addresses || [],
    txt: service.txt || {},
    type: service.type,
    protocol: service.protocol,
    updatedAt: new Date().toISOString(),
  });
  console.log('Service up', service.name || '<unknown>', id);
});

browser.on('down', (service) => {
  if (!service) {
    console.warn('Bonjour emitted "down" with undefined service');
    return;
  }
  const id = serviceId(service);
  services.delete(id);
  console.log('Service down', service.name || '<unknown>', id);
});

app.get('/api/servers', (req, res) => {
  let list = Array.from(services.values());
  const q = req.query.name;
  if (q) {
    const qLower = String(q).toLowerCase();
    list = list.filter((s) => (s.name || '').toLowerCase().includes(qLower));
  } else if (SERVICE_NAME_FILTER) {
    list = list.filter((s) => (s.name || '').toLowerCase().includes(SERVICE_NAME_FILTER.toLowerCase()));
  }
  res.json(list);
});

app.get('/health', (req, res) => res.json({ ok: true, count: services.size }));

const server = app.listen(PORT, () => {
  console.log(`Discovery server listening on http://localhost:${PORT}`);
});

process.on('SIGINT', () => {
  console.log('Shutting down discovery server...');
  browser.stop();
  server.close(() => process.exit(0));
});
