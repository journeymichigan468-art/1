const requests = new Map();

const WINDOW_MS = 60 * 1000;
const MAX_REQUESTS = 10;

function limiter(req, res, next) {
  const key = req.user?.sub || req.ip;
  const now = Date.now();
  const record = requests.get(key) || { count: 0, start: now };

  if (now - record.start > WINDOW_MS) {
    record.count = 0;
    record.start = now;
  }

  record.count += 1;
  requests.set(key, record);

  if (record.count > MAX_REQUESTS) {
    return res
      .status(429)
      .json({ error: 'Too many requests, please try again later.' });
  }

  return next();
}

module.exports = { limiter };
